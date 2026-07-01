"""
在线检索模块：查询改写 + 双路混合检索（dense + BM25）+ RRF 融合。
"""
from __future__ import annotations

from pymilvus import AnnSearchRequest, RRFRanker

from RAG.config import config
from RAG.clients import embed_single, get_llm_client, get_milvus_client
from util.log import get_logger

logger = get_logger(__name__)


def _to_int(value):
    """安全转 int，避免 Milvus 返回字符串时影响后续逻辑。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def rewrite_query(user_query: str, system_prompt: str | None = None) -> str:
    """
    使用当前知识库的改写提示词，把口语化问题压缩成更适合检索的查询。
    改写失败时回退原问题，保证流程不中断。
    """
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=config.llm_rewrite_model,
            messages=[
                {"role": "system", "content": system_prompt or config.rewrite_system_prompt},
                {"role": "user", "content": user_query},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        rewritten = response.choices[0].message.content.strip()
        logger.info(
            "[%s] 查询改写: '%s' -> '%s'",
            config.active_kb_id,
            user_query[:60],
            rewritten[:60],
        )
        return rewritten
    except Exception as exc:
        logger.warning("[%s] 查询改写失败，回退原问题: %s", config.active_kb_id, exc)
        return user_query


def hybrid_search(
    query_text: str,
    query_vector: list[float],
    top_k: int | None = None,
    filter_expr: str | None = None,
) -> list[dict]:
    """
    执行稠密向量 + BM25 的混合检索，并把结果统一成内部候选结构。
    """
    client = get_milvus_client()
    top_k = top_k or config.hybrid_top_k

    req_dense = AnnSearchRequest(
        data=[query_vector],
        anns_field="dense_vector",
        param={"metric_type": "COSINE", "nprobe": 16},
        limit=top_k,
    )
    req_sparse = AnnSearchRequest(
        data=[query_text],
        anns_field="sparse_vector",
        param={"metric_type": "BM25"},
        limit=top_k,
    )
    ranker = RRFRanker(k=config.rrf_k)

    try:
        results = client.hybrid_search(
            collection_name=config.milvus_collection_name,
            reqs=[req_dense, req_sparse],
            ranker=ranker,
            limit=config.rrf_final_n,
            filter=filter_expr or "",
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
        )
    except Exception as exc:
        logger.error(
            "[%s] hybrid_search 失败: collection=%s, filter=%s, error=%s",
            config.active_kb_id,
            config.milvus_collection_name,
            filter_expr or "<empty>",
            exc,
        )
        raise

    candidates: list[dict] = []
    for hits in results:
        for hit in hits:
            entity = hit.get("entity", hit)
            candidates.append(
                {
                    "id": str(entity.get("id", "")),
                    "doc_id": entity.get("doc_id", ""),
                    "text": entity.get("text", ""),
                    "question": entity.get("question", ""),
                    "answer": entity.get("answer", ""),
                    "reason": entity.get("reason", ""),
                    "file_name": entity.get("file_name", ""),
                    "chunk_index": _to_int(entity.get("chunk_index", 0)),
                    "total_chunks": _to_int(entity.get("total_chunks", 0)),
                    "source_type": entity.get("source_type", ""),
                    "score": hit.get("distance", hit.get("score", 0.0)),
                }
            )

    logger.info(
        "[%s] 混合检索完成: collection=%s, filter=%s, candidates=%d",
        config.active_kb_id,
        config.milvus_collection_name,
        filter_expr or "<empty>",
        len(candidates),
    )
    return candidates


def search_with_rewrite(user_query: str, filter_expr: str | None = None) -> list[dict]:
    """查询改写 + Embedding + 混合检索的便捷封装。"""
    rewritten = rewrite_query(user_query)
    query_vector = embed_single(rewritten)
    return hybrid_search(rewritten, query_vector, filter_expr=filter_expr)
