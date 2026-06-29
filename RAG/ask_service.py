"""
RAG 问答编排服务。

这里把多知识库、QA 优先、原文回退、证据不足拒答等流程串起来，
供 CLI、HTTP 接口和批量评测统一复用。
"""
from __future__ import annotations

import re
import time
from typing import Any

from RAG.config import config
from RAG.generation import generate_answer
from RAG.prompt_builder import build_prompt
from RAG.retrieval_service import RetrievedChunk, prepare_query, search_context
from util.log import get_logger

logger = get_logger(__name__)

_REFUSE_TEXT = "资料不足，无法确定。当前知识库中没有足够依据支持回答该问题。"
_PROJECT_SELF_TERMS = ("本工程", "本项目")
_REFERENCE_TERMS = ("参考", "对标", "福建项目")
# 轻量领域词表：先解决当前 production QA 直返容易串到“参考项目”的问题。
_QA_HINT_TERMS = (
    "单机容量",
    "总装机容量",
    "装机容量",
    "接线方式",
    "常浪向",
    "风速",
    "风机",
    "海缆",
    "升压站",
    "潮位",
    "潮流",
    "波浪",
    "波高",
    "工期",
    "投资",
    "风资源",
    "主变",
    "集电系统",
    "送出海缆",
    "配置",
    "基础",
    "抗震",
    "防撞",
    "轮毂高度",
)


def ask_question(
    question: str,
    kb_id: str,
    enable_rerank: bool | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """
    对外统一问答入口。

    返回格式尽量贴近现有 controller，避免 CLI / HTTP / 评测层重复适配。
    """
    with config.use_kb(kb_id):
        t_start = time.time()
        rerank_enabled = enable_rerank if enable_rerank is not None else config.enable_rerank
        trace: dict[str, Any] = {
            "kb_id": kb_id,
            "collection_name": config.milvus_collection_name,
        }

        preparation = prepare_query(question)
        trace["rewrite_ms"] = preparation.rewrite_ms
        trace["embed_ms"] = preparation.embed_ms

        if config.current_kb.qa_direct_enabled:
            result = _ask_with_qa_first(
                question=question,
                rerank_enabled=rerank_enabled,
                top_k=top_k,
                trace=trace,
                preparation=preparation,
            )
        else:
            result = _ask_with_single_stage(
                question=question,
                rerank_enabled=rerank_enabled,
                top_k=top_k,
                trace=trace,
                preparation=preparation,
            )

        trace["total_ms"] = round((time.time() - t_start) * 1000, 1)
        result["trace"] = trace
        result["rewritten_query"] = (
            preparation.rewritten_query if preparation.rewritten_query != question else None
        )
        result["question"] = question
        return result


def _ask_with_single_stage(
    question: str,
    rerank_enabled: bool,
    top_k: int | None,
    trace: dict[str, Any],
    preparation,
) -> dict[str, Any]:
    """兼容旧四大名著链路：直接检索 -> Prompt -> LLM。"""
    retrieval = search_context(
        question,
        enable_rerank=rerank_enabled,
        top_k=top_k,
        prepared=preparation,
    )
    trace["candidate_count"] = len(retrieval.chunks)
    trace["final_count"] = len(retrieval.chunks)
    trace["answer_mode"] = "retrieve_answer"

    prompt_result = _generate_answer_from_chunks(question, retrieval.chunks, trace)
    prompt_result["trace"]["fallback"] = prompt_result["fallback"]
    return prompt_result


def _ask_with_qa_first(
    question: str,
    rerank_enabled: bool,
    top_k: int | None,
    trace: dict[str, Any],
    preparation,
) -> dict[str, Any]:
    """工程库链路：先查 QA，命中稳则直返，否则回退原文检索。"""
    qa_result = search_context(
        question,
        enable_rerank=rerank_enabled,
        top_k=top_k,
        filter_expr='source_type == "qa"',
        prepared=preparation,
    )
    qa_chunks = _rerank_qa_chunks(question, qa_result.chunks)
    trace["qa_candidate_count"] = len(qa_result.chunks)
    trace["qa_filtered_count"] = len(qa_chunks)
    trace["qa_top_score"] = _score_of(qa_chunks, 0)
    trace["qa_second_score"] = _score_of(qa_chunks, 1)

    if _should_direct_answer(qa_chunks):
        top_chunk = qa_chunks[0]
        trace["candidate_count"] = len(qa_chunks)
        trace["final_count"] = 1
        trace["answer_mode"] = "qa_direct"
        trace["fallback"] = False
        logger.info("[%s] QA 直返命中: %s", config.active_kb_id, top_chunk.file_name)
        return {
            "answer": top_chunk.answer,
            "citations": [_build_direct_citation(top_chunk)],
            "model": "qa_direct",
            "generate_ms": 0,
            "fallback": False,
            "trace": trace,
        }

    retrieval = search_context(
        question,
        enable_rerank=rerank_enabled,
        top_k=top_k,
        filter_expr='source_type != "qa"',
        prepared=preparation,
    )
    trace["candidate_count"] = len(retrieval.chunks)
    trace["final_count"] = len(retrieval.chunks)
    trace["doc_top_score"] = _score_of(retrieval.chunks, 0)

    if _should_refuse(retrieval.chunks):
        trace["answer_mode"] = "refuse"
        trace["fallback"] = False
        logger.info("[%s] 证据不足，直接拒答", config.active_kb_id)
        return {
            "answer": _REFUSE_TEXT,
            "citations": [],
            "model": "refuse",
            "generate_ms": 0,
            "fallback": False,
            "trace": trace,
        }

    trace["answer_mode"] = "retrieve_answer"
    prompt_result = _generate_answer_from_chunks(question, retrieval.chunks, trace)
    prompt_result["trace"]["fallback"] = prompt_result["fallback"]
    return prompt_result


def _rerank_qa_chunks(question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """
    对 QA 候选做一层轻量校正，优先避免“本项目”问题误命中“参考项目”答案。

    这里只做小步增强，不改底层检索结构，也不做一次性大重构。
    """
    if not chunks or config.active_kb_id != "production":
        return chunks

    return sorted(
        chunks,
        key=lambda chunk: (_qa_adjusted_score(question, chunk), float(chunk.score or 0.0)),
        reverse=True,
    )


def _qa_adjusted_score(question: str, chunk: RetrievedChunk) -> float:
    """给 QA 候选叠加少量业务判别分，尽量保守，但减少误直返。"""
    score = float(chunk.score or 0.0)
    merged_text = _merge_qa_text(chunk)

    if _is_self_project_question(question):
        if _is_reference_candidate(merged_text):
            score -= 0.25
        elif any(term in merged_text for term in _PROJECT_SELF_TERMS):
            score += 0.05

    overlap = sum(1 for keyword in _extract_question_hints(question) if keyword in merged_text)
    score += min(0.12, overlap * 0.03)
    return score


def _extract_question_hints(question: str) -> list[str]:
    """抽取少量可解释的领域关键词，供 QA 候选重排使用。"""
    hints = [term for term in _QA_HINT_TERMS if term in question]
    hints.extend(re.findall(r"\d+(?:\.\d+)?\s*(?:MW|kV|m/s|m|%)", question, flags=re.IGNORECASE))
    return hints


def _merge_qa_text(chunk: RetrievedChunk) -> str:
    """把 QA 候选的问、答、原因合并，便于做简单规则判断。"""
    return f"{chunk.question} {chunk.answer} {chunk.reason}"


def _is_self_project_question(question: str) -> bool:
    """当前是否是“本项目 / 本工程”主语的问题。"""
    return any(term in question for term in _PROJECT_SELF_TERMS) and not _is_reference_candidate(question)


def _is_reference_candidate(text: str) -> bool:
    """候选是否明显在说参考项目，而不是当前工程本体。"""
    return any(term in text for term in _REFERENCE_TERMS)


def _generate_answer_from_chunks(
    question: str,
    chunks: list[RetrievedChunk],
    trace: dict[str, Any],
) -> dict[str, Any]:
    """把检索结果转成 Prompt，再交给 LLM 生成答案。"""
    candidates = [
        {
            "doc_id": chunk.source_id,
            "file_name": chunk.file_name,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "source_type": chunk.source_type,
            "question": chunk.question,
            "answer": chunk.answer,
            "reason": chunk.reason,
            "total_chunks": chunk.total_chunks,
            "rerank_score": chunk.score,
        }
        for chunk in chunks
    ]

    t0 = time.time()
    prompt = build_prompt(question, candidates)
    trace["prompt_ms"] = round((time.time() - t0) * 1000, 1)
    trace["context_tokens"] = prompt["context_tokens"]
    trace["context_blocks"] = len(prompt["context_blocks"])

    result = generate_answer(
        user_query=question,
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        citations=prompt["citations"],
    )
    trace["generate_ms"] = result["generate_ms"]
    return {**result, "trace": trace}


def _should_direct_answer(chunks: list[RetrievedChunk]) -> bool:
    """判断 QA Top1 是否足够稳，满足则直接返回标准答案。"""
    if not chunks:
        return False

    top_score = _score_of(chunks, 0)
    second_score = _score_of(chunks, 1)
    margin = top_score - second_score
    kb = config.current_kb
    return (
        top_score >= kb.qa_direct_threshold
        and bool(chunks[0].answer)
        and (top_score >= 0.95 or margin >= kb.qa_margin_threshold)
    )


def _should_refuse(chunks: list[RetrievedChunk]) -> bool:
    """工程库要求保守回答：证据太弱就明确拒答。"""
    if not config.current_kb.refuse_when_insufficient:
        return False
    if not chunks:
        return True
    return _score_of(chunks, 0) < config.current_kb.retrieval_min_score


def _score_of(chunks: list[RetrievedChunk], index: int) -> float:
    """安全读取某个候选的分数，避免空列表异常。"""
    if index >= len(chunks):
        return 0.0
    return float(chunks[index].score or 0.0)


def _build_direct_citation(chunk: RetrievedChunk) -> dict[str, Any]:
    """构建 QA 直返场景下的来源信息。"""
    return {
        "source_id": 1,
        "file_name": chunk.file_name,
        "source_type": chunk.source_type,
        "chunk_index": chunk.chunk_index,
        "text_preview": chunk.question[:100],
        "answer_preview": chunk.answer[:100],
    }
