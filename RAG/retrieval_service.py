"""
RAG 检索服务层 — 提供纯粹的检索能力（不生成最终答案）。

Agent 工具、CLI、HTTP controller 统一复用此模块。
"""
import time
from pydantic import BaseModel, Field

from RAG.config import config
from RAG.retrieval import rewrite_query, hybrid_search
from RAG.clients import embed_single
from RAG.rerank import rerank
from util.log import get_logger

logger = get_logger(__name__)


class RetrievedChunk(BaseModel):
    source_id: str
    file_name: str
    chunk_index: int
    score: float | None = None
    text: str
    text_preview: str | None = None
    source_type: str = ""


class RetrievalResult(BaseModel):
    question: str
    rewritten_query: str
    chunks: list[RetrievedChunk]
    retrieval_ms: int
    rerank_enabled: bool = True


def search_context(question: str, enable_rerank: bool = True) -> RetrievalResult:
    """
    检索知识库，返回相关上下文片段（不含 LLM 生成）。

    Args:
        question: 用户原始问题
        enable_rerank: 是否启用 CrossEncoder 精排

    Returns:
        RetrievalResult: 包含改写后查询和检索片段列表
    """
    t_start = time.time()

    # 1. 查询改写
    rewritten = rewrite_query(question)
    logger.info("[retrieval_service] 查询改写: '%s' → '%s'", question[:60], rewritten[:60])

    # 2. Embedding
    query_vector = embed_single(rewritten)

    # 3. 混合检索
    candidates = hybrid_search(rewritten, query_vector)
    logger.info("[retrieval_service] 混合检索: %d 候选", len(candidates))

    # 4. 精排
    rerank_enabled = enable_rerank and config.enable_rerank
    if rerank_enabled:
        candidates = rerank(question, candidates)
        logger.info("[retrieval_service] 精排完成: Top-%d", len(candidates))
    else:
        candidates = candidates[:config.rerank_top_k]

    # 5. 转为结构化结果
    chunks = []
    for c in candidates:
        text = c.get("text", "")
        chunks.append(RetrievedChunk(
            source_id=c.get("doc_id", ""),
            file_name=c.get("file_name", ""),
            chunk_index=c.get("chunk_index", 0),
            score=c.get("rerank_score", c.get("score")),
            text=text,
            text_preview=text[:120].replace("\n", " "),
            source_type=c.get("source_type", ""),
        ))

    retrieval_ms = int((time.time() - t_start) * 1000)
    logger.info("[retrieval_service] 检索完成: %d chunks, %dms", len(chunks), retrieval_ms)

    return RetrievalResult(
        question=question,
        rewritten_query=rewritten if rewritten != question else question,
        chunks=chunks,
        retrieval_ms=retrieval_ms,
        rerank_enabled=rerank_enabled,
    )
