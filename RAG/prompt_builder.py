"""
结果组装模块：small-to-big 邻居合并、去重、Token 预算、Prompt 组装。
"""
from pymilvus import Collection

from RAG.config import config
from RAG.clients import get_milvus_client, _ensure_orm_connection
from util.log import get_logger

logger = get_logger(__name__)


def _to_int(v) -> int:
    """安全转 int，处理 Milvus 返回的字符串类型"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def fetch_neighbors(candidates: list[dict]) -> list[dict]:
    """
    small-to-big retrieval：对每个命中 chunk，拉取其前后相邻 chunk。

    在当前 Collection 中按 doc_id 查找相邻 chunk_index。
    """
    if not candidates:
        return []

    _ensure_orm_connection()
    client = get_milvus_client()
    expanded = {}
    collection = Collection(config.milvus_collection_name)

    for c in candidates:
        doc_id = c.get("doc_id", "")
        chunk_idx = _to_int(c.get("chunk_index"))

        # 计算邻居索引：当前 ± 1
        neighbor_indices = set()
        if chunk_idx > 0:
            neighbor_indices.add(chunk_idx - 1)
        neighbor_indices.add(chunk_idx)
        neighbor_indices.add(chunk_idx + 1)

        for ni in sorted(neighbor_indices):
            key = f"{doc_id}_{ni}"
            if key in expanded:
                continue

            # 如果就是当前 chunk，直接保留
            if ni == chunk_idx:
                expanded[key] = c
                continue

            # 查询邻居
            try:
                results = collection.query(
                    expr=f'doc_id == "{doc_id}" and chunk_index == {ni}',
                    output_fields=[
                        "doc_id", "text", "question", "answer", "reason",
                        "file_name", "chunk_index", "total_chunks", "source_type",
                    ],
                    limit=1,
                )
                if results:
                    r = results[0]
                    expanded[key] = {
                        "id": str(r.get("id", "")),
                        "doc_id": r.get("doc_id", ""),
                        "text": r.get("text", ""),
                        "question": r.get("question", ""),
                        "answer": r.get("answer", ""),
                        "reason": r.get("reason", ""),
                        "file_name": r.get("file_name", ""),
                        "chunk_index": _to_int(r.get("chunk_index")),
                        "total_chunks": _to_int(r.get("total_chunks")),
                        "source_type": r.get("source_type", ""),
                        "score": c.get("score", 0),
                        "rerank_score": c.get("rerank_score", 0),
                        "is_neighbor": ni != chunk_idx,
                    }
            except Exception as e:
                logger.debug("查询邻居失败 doc_id=%s chunk=%d: %s", doc_id, ni, e)

    result = list(expanded.values())
    logger.debug("small-to-big: %d → %d", len(candidates), len(result))
    return result


def deduplicate(candidates: list[dict], threshold: float = 0.85) -> list[dict]:
    """
    去重：先按(doc_id, chunk_index)去重，再按 Jaccard 相似度去重。

    保留分数更高的版本。
    """
    if not candidates:
        return []

    # 第一层：按 (doc_id, chunk_index) 去重
    seen_keys = set()
    layer1 = []
    for c in sorted(candidates, key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True):
        key = (c.get("doc_id"), _to_int(c.get("chunk_index")))
        if key not in seen_keys:
            seen_keys.add(key)
            layer1.append(c)

    # 第二层：Jaccard 相似度去重
    deduped = []
    seen_texts = []

    for c in layer1:
        is_dup = False
        c_chars = set(c.get("text", ""))
        if not c_chars:
            continue

        for s_text in seen_texts:
            s_chars = set(s_text)
            intersection = len(c_chars & s_chars)
            union = len(c_chars | s_chars)
            if union == 0:
                continue
            if intersection / union > threshold:
                is_dup = True
                break

        if not is_dup:
            deduped.append(c)
            seen_texts.append(c.get("text", ""))

    return deduped


def estimate_tokens(text: str) -> int:
    """保守估计 token 数：中文字符约 0.5 token，这里取 1:1 上限"""
    return len(text)


def build_context_blocks(candidates: list[dict], max_tokens: int | None = None) -> tuple[list[dict], int]:
    """
    按 Token 预算组装上下文块。

    Returns:
        (selected_blocks, total_tokens)
    """
    max_tokens = max_tokens or config.max_context_tokens
    blocks = []
    token_count = 0

    # 优先非邻居 + 高分在前
    sorted_candidates = sorted(
        candidates,
        key=lambda x: (
            x.get("is_neighbor", False),           # 非邻居优先
            -(x.get("rerank_score", x.get("score", 0))),  # 高分优先
        ),
    )

    for c in sorted_candidates:
        text = c.get("text", "")
        chunk_tokens = estimate_tokens(text)

        if token_count + chunk_tokens > max_tokens:
            # 截断最后一条
            remaining = max_tokens - token_count
            if remaining > 80:  # 至少保留 80 字有意义的内容
                c = {**c, "text": text[:remaining * 2] + "..."}
                blocks.append(c)
                token_count += remaining
            break

        blocks.append(c)
        token_count += chunk_tokens

    return blocks, token_count


def format_context(block: dict, index: int) -> str:
    """格式化单个上下文块，带来源标记。QA 对用问答格式，文档用原文格式。"""
    file_name = block.get("file_name", "未知")
    source_type = block.get("source_type", "")
    chunk_idx = _to_int(block.get("chunk_index"))
    total = _to_int(block.get("total_chunks"))
    text = block.get("text", "")

    if source_type == "qa":
        question = block.get("question", "")
        answer = block.get("answer", "")
        reason = block.get("reason", "")
        return (
            f"[来源 {index} | QA问答对 | {file_name} | #{chunk_idx + 1}/{total}]\n"
            f"问题: {question}\n"
            f"答案: {answer}\n"
            f"依据: {reason}"
        )

    return (
        f"[来源 {index} | 文档原文 | {file_name} | chunk {chunk_idx + 1}/{total}]\n"
        f"{text}"
    )


def build_prompt(
    user_query: str,
    candidates: list[dict],
    max_tokens: int | None = None,
) -> dict:
    """
    组装最终 RAG Prompt。

    Returns:
        {
            "system_prompt": str,
            "user_prompt": str,
            "context_blocks": list[dict],
            "context_tokens": int,
            "citations": list[dict],
        }
    """
    # small-to-big
    expanded = fetch_neighbors(candidates)

    # 去重
    deduped = deduplicate(expanded)

    # Token 预算
    blocks, token_count = build_context_blocks(deduped, max_tokens)

    # 组装上下文
    context_parts = []
    citations = []
    for i, block in enumerate(blocks, 1):
        context_parts.append(format_context(block, i))
        citations.append({
            "source_id": i,
            "file_name": block.get("file_name", ""),
            "source_type": block.get("source_type", ""),
            "chunk_index": _to_int(block.get("chunk_index")),
            "text_preview": (block.get("question") or block.get("text", ""))[:100],
            "answer_preview": block.get("answer", "")[:100],
        })

    context_text = "\n\n---\n\n".join(context_parts)

    system_prompt = (
        "你是一个四大名著知识问答助手。请严格基于下面提供的上下文信息回答问题。\n\n"
        "规则：\n"
        "1. 只能基于上下文回答，不要使用外部知识。\n"
        "2. 如果上下文不足以回答问题，请明确说「资料不足，无法确定」。\n"
        "3. 回答中引用来源编号，例如 [来源 1]。\n"
        "4. 不要编造文件名、页码或不存在的引用。\n"
        "5. 简洁准确，直接回答核心问题。"
    )

    user_prompt = (
        f"## 参考资料\n\n{context_text}\n\n"
        f"## 用户问题\n\n{user_query}\n\n"
        f"请基于以上参考资料回答问题。"
    )

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "context_blocks": blocks,
        "context_tokens": token_count,
        "citations": citations,
    }
