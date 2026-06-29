"""
RAG 检索服务层：负责查询准备、向量检索和精排。

这个模块只处理“把什么片段找出来”，不直接负责最终回答文案。
"""
from __future__ import annotations

import time

from pydantic import BaseModel

from RAG.config import config
from RAG.clients import embed_single
from RAG.rerank import rerank
from RAG.retrieval import hybrid_search, rewrite_query
from util.log import get_logger

logger = get_logger(__name__)


class QueryPreparation(BaseModel):
    """保存一次查询改写和 Embedding 结果，便于多阶段检索复用。"""

    question: str
    rewritten_query: str
    query_vector: list[float]
    rewrite_ms: int
    embed_ms: int


class RetrievedChunk(BaseModel):
    """统一的检索结果结构。"""

    source_id: str
    file_name: str
    chunk_index: int
    total_chunks: int = 0
    score: float | None = None
    text: str
    text_preview: str | None = None
    source_type: str = ""
    question: str = ""
    answer: str = ""
    reason: str = ""


class RetrievalResult(BaseModel):
    """一次检索执行的完整返回值。"""

    question: str
    rewritten_query: str
    chunks: list[RetrievedChunk]
    retrieval_ms: int
    rerank_enabled: bool = True
    filter_expr: str | None = None


def prepare_query(question: str) -> QueryPreparation:
    """先做一次查询改写和 Embedding，后续多阶段检索直接复用。"""
    t0 = time.time()
    rewritten = rewrite_query(question)
    rewrite_ms = int((time.time() - t0) * 1000)

    t1 = time.time()
    query_vector = embed_single(rewritten)
    embed_ms = int((time.time() - t1) * 1000)

    logger.info(
        "[%s] 查询准备完成: rewrite=%dms, embed=%dms",
        config.active_kb_id,
        rewrite_ms,
        embed_ms,
    )
    return QueryPreparation(
        question=question,
        rewritten_query=rewritten if rewritten else question,
        query_vector=query_vector,
        rewrite_ms=rewrite_ms,
        embed_ms=embed_ms,
    )


def search_context(
    question: str,
    enable_rerank: bool = True,
    filter_expr: str | None = None,
    top_k: int | None = None,
    prepared: QueryPreparation | None = None,
) -> RetrievalResult:
    """
    检索知识库，返回结构化片段列表。

    支持传入预处理结果，这样像“先查 QA，再查原文”的场景就不会重复做改写和 Embedding。
    """
    preparation = prepared or prepare_query(question)
    t_start = time.time()

    candidates = hybrid_search(
        preparation.rewritten_query,
        preparation.query_vector,
        top_k=top_k,
        filter_expr=filter_expr,
    )
    logger.info(
        "[%s] 混合检索返回 %d 个候选, filter=%s",
        config.active_kb_id,
        len(candidates),
        filter_expr or "<empty>",
    )

    rerank_enabled = enable_rerank and config.enable_rerank
    if rerank_enabled:
        candidates = rerank(question, candidates, top_k=top_k or config.rerank_top_k)
        logger.info("[%s] 精排完成: Top-%d", config.active_kb_id, len(candidates))
    else:
        candidates = candidates[: (top_k or config.rerank_top_k)]

    chunks = []
    for candidate in candidates:
        text = candidate.get("text", "")
        chunks.append(
            RetrievedChunk(
                source_id=candidate.get("doc_id", ""),
                file_name=candidate.get("file_name", ""),
                chunk_index=candidate.get("chunk_index", 0),
                total_chunks=candidate.get("total_chunks", 0),
                score=candidate.get("rerank_score", candidate.get("score")),
                text=text,
                text_preview=(candidate.get("question") or text)[:120].replace("\n", " "),
                source_type=candidate.get("source_type", ""),
                question=candidate.get("question", ""),
                answer=candidate.get("answer", ""),
                reason=candidate.get("reason", ""),
            )
        )

    retrieval_ms = int((time.time() - t_start) * 1000)
    logger.info(
        "[%s] 检索完成: chunks=%d, %dms, filter=%s",
        config.active_kb_id,
        len(chunks),
        retrieval_ms,
        filter_expr or "<empty>",
    )
    return RetrievalResult(
        question=question,
        rewritten_query=preparation.rewritten_query,
        chunks=chunks,
        retrieval_ms=retrieval_ms,
        rerank_enabled=rerank_enabled,
        filter_expr=filter_expr,
    )
