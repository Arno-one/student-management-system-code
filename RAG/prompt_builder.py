"""
结果组装模块：small-to-big 邻居合并、去重、Token 预算和 Prompt 组装。
"""
from __future__ import annotations

from pymilvus import Collection

from RAG.clients import _ensure_orm_connection
from RAG.config import config
from util.log import get_logger

logger = get_logger(__name__)


def _to_int(value) -> int:
    """安全转 int，处理 Milvus 返回的字符串值。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def fetch_neighbors(candidates: list[dict]) -> list[dict]:
    """
    small-to-big retrieval：对命中的每个 chunk 拉取前后相邻片段。
    这样在回答长段落问题时，上下文会更完整。
    """
    if not candidates:
        return []

    _ensure_orm_connection()
    collection = Collection(config.milvus_collection_name)
    expanded: dict[str, dict] = {}

    for candidate in candidates:
        doc_id = candidate.get("doc_id", "")
        chunk_index = _to_int(candidate.get("chunk_index"))

        neighbor_indices = {chunk_index}
        if chunk_index > 0:
            neighbor_indices.add(chunk_index - 1)
        neighbor_indices.add(chunk_index + 1)

        for neighbor_index in sorted(neighbor_indices):
            cache_key = f"{doc_id}_{neighbor_index}"
            if cache_key in expanded:
                continue

            if neighbor_index == chunk_index:
                expanded[cache_key] = candidate
                continue

            try:
                results = collection.query(
                    expr=f'doc_id == "{doc_id}" and chunk_index == {neighbor_index}',
                    output_fields=[
                        "doc_id",
                        "text",
                        "question",
                        "answer",
                        "reason",
                        "file_name",
                        "chunk_index",
                        "total_chunks",
                        "source_type",
                    ],
                    limit=1,
                )
                if not results:
                    continue

                row = results[0]
                expanded[cache_key] = {
                    "id": str(row.get("id", "")),
                    "doc_id": row.get("doc_id", ""),
                    "text": row.get("text", ""),
                    "question": row.get("question", ""),
                    "answer": row.get("answer", ""),
                    "reason": row.get("reason", ""),
                    "file_name": row.get("file_name", ""),
                    "chunk_index": _to_int(row.get("chunk_index")),
                    "total_chunks": _to_int(row.get("total_chunks")),
                    "source_type": row.get("source_type", ""),
                    "score": candidate.get("score", 0),
                    "rerank_score": candidate.get("rerank_score", 0),
                    "is_neighbor": True,
                }
            except Exception as exc:
                logger.debug("查询邻居失败 doc_id=%s chunk=%d: %s", doc_id, neighbor_index, exc)

    result = list(expanded.values())
    logger.debug("small-to-big: %d -> %d", len(candidates), len(result))
    return result


def deduplicate(candidates: list[dict], threshold: float = 0.85) -> list[dict]:
    """先按 (doc_id, chunk_index) 去重，再按文本 Jaccard 相似度做一轮软去重。"""
    if not candidates:
        return []

    first_layer = []
    seen_keys: set[tuple[str, int]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: item.get("rerank_score", item.get("score", 0)),
        reverse=True,
    ):
        key = (candidate.get("doc_id", ""), _to_int(candidate.get("chunk_index")))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        first_layer.append(candidate)

    deduped = []
    seen_texts: list[str] = []
    for candidate in first_layer:
        text = candidate.get("text", "")
        text_chars = set(text)
        if not text_chars:
            continue

        is_dup = False
        for seen_text in seen_texts:
            seen_chars = set(seen_text)
            union = len(text_chars | seen_chars)
            if union == 0:
                continue
            if len(text_chars & seen_chars) / union > threshold:
                is_dup = True
                break

        if not is_dup:
            deduped.append(candidate)
            seen_texts.append(text)

    return deduped


def estimate_tokens(text: str) -> int:
    """保守估算 Token 数，中文场景先按 1 字符约等于 1 token 上限处理。"""
    return len(text)


def build_context_blocks(candidates: list[dict], max_tokens: int | None = None) -> tuple[list[dict], int]:
    """按 Token 预算裁出本轮真正送给 LLM 的上下文块。"""
    budget = max_tokens or config.max_context_tokens
    blocks = []
    token_count = 0

    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            item.get("is_neighbor", False),  # 非邻居优先
            -(item.get("rerank_score", item.get("score", 0))),
        ),
    )

    for candidate in sorted_candidates:
        text = candidate.get("text", "")
        chunk_tokens = estimate_tokens(text)

        if token_count + chunk_tokens > budget:
            remaining = budget - token_count
            if remaining > 80:
                truncated = {**candidate, "text": text[: remaining * 2] + "..."}
                blocks.append(truncated)
                token_count += remaining
            break

        blocks.append(candidate)
        token_count += chunk_tokens

    return blocks, token_count


def format_context(block: dict, index: int) -> str:
    """把单个上下文块格式化成最终 Prompt 里的可读片段。"""
    file_name = block.get("file_name", "未知")
    source_type = block.get("source_type", "")
    chunk_index = _to_int(block.get("chunk_index"))
    total_chunks = _to_int(block.get("total_chunks"))
    text = block.get("text", "")

    if source_type == "qa":
        return (
            f"[来源 {index} | QA问答对 | {file_name} | #{chunk_index + 1}/{total_chunks}]\n"
            f"问题: {block.get('question', '')}\n"
            f"答案: {block.get('answer', '')}\n"
            f"依据: {block.get('reason', '')}"
        )

    return (
        f"[来源 {index} | 文档原文 | {file_name} | chunk {chunk_index + 1}/{total_chunks}]\n"
        f"{text}"
    )


def build_prompt(user_query: str, candidates: list[dict], max_tokens: int | None = None) -> dict:
    """把检索片段组装成最终发给 LLM 的 Prompt。"""
    expanded = fetch_neighbors(candidates)
    deduped = deduplicate(expanded)
    blocks, token_count = build_context_blocks(deduped, max_tokens)

    context_parts = []
    citations = []
    for index, block in enumerate(blocks, 1):
        context_parts.append(format_context(block, index))
        citations.append(
            {
                "source_id": index,
                "file_name": block.get("file_name", ""),
                "source_type": block.get("source_type", ""),
                "chunk_index": _to_int(block.get("chunk_index")),
                "text_preview": (block.get("question") or block.get("text", ""))[:100],
                "answer_preview": block.get("answer", "")[:100],
            }
        )

    context_text = "\n\n---\n\n".join(context_parts)
    user_prompt = (
        f"## 参考资料\n\n{context_text}\n\n"
        f"## 用户问题\n\n{user_query}\n\n"
        "请基于以上参考资料回答问题。"
    )

    return {
        "system_prompt": config.answer_system_prompt,
        "user_prompt": user_prompt,
        "context_blocks": blocks,
        "context_tokens": token_count,
        "citations": citations,
    }
