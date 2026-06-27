"""
在线检索模块：查询改写 + 双路混合检索(dense + BM25) + RRF 融合。
"""
import hashlib
from pymilvus import AnnSearchRequest, RRFRanker

from RAG.config import config
from RAG.clients import embed_single, get_llm_client, get_milvus_client
from util.log import get_logger

logger = get_logger(__name__)


def _to_int(v):
    """安全转 int"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def rewrite_query(user_query: str) -> str:
    """
    LLM 查询改写：口语化问题 → 关键词密集的检索查询。

    改写失败时返回原始问题，保证流程不中断。
    """
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=config.llm_rewrite_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是搜索查询优化器。将用户的口语化问题改写为简洁、关键词密集的检索查询。"
                        "保留所有专有名词。只输出改写后的查询，不要解释。"
                        "如果用户问的是四大名著相关，保留人物名、地名、事件名等关键信息。"
                    ),
                },
                {"role": "user", "content": user_query},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        rewritten = response.choices[0].message.content.strip()
        logger.info("查询改写: '%s' → '%s'", user_query[:60], rewritten[:60])
        return rewritten
    except Exception as e:
        logger.warning("查询改写失败，使用原始问题: %s", e)
        return user_query


def hybrid_search(
    query_text: str,
    query_vector: list[float],
    top_k: int | None = None,
    filter_expr: str | None = None,
) -> list[dict]:
    """
    双路混合检索：稠密向量 + BM25 → RRF 融合。

    Args:
        query_text: 改写后的检索文本（用于 BM25）
        query_vector: 1024 维稠密向量
        top_k: RRF 融合后返回数量
        filter_expr: Milvus 标量过滤表达式

    Returns:
        [{id, doc_id, text, file_name, chunk_index, total_chunks, source_type, score}, ...]
    """
    client = get_milvus_client()
    top_k = top_k or config.hybrid_top_k

    # 稠密检索
    req_dense = AnnSearchRequest(
        data=[query_vector],
        anns_field="dense_vector",
        param={"metric_type": "COSINE", "nprobe": 16},
        limit=top_k,
    )

    # BM25 稀疏检索（传原始文本）
    req_sparse = AnnSearchRequest(
        data=[query_text],
        anns_field="sparse_vector",
        param={"metric_type": "BM25"},
        limit=top_k,
    )

    # RRF 融合
    ranker = RRFRanker(k=config.rrf_k)

    try:
        results = client.hybrid_search(
            collection_name=config.milvus_collection_name,
            reqs=[req_dense, req_sparse],
            ranker=ranker,
            limit=config.rrf_final_n,
            filter=filter_expr or "",
            output_fields=[
                "doc_id", "text", "question", "answer", "reason",
                "file_name", "chunk_index", "total_chunks", "source_type",
            ],
        )
    except Exception as e:
        logger.error("hybrid_search 失败: %s", e)
        raise

    # 统一为 candidate 结构
    candidates = []
    for hits in results:
        for hit in hits:
            entity = hit.get("entity", hit)
            candidates.append({
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
            })

    logger.info(
        "混合检索: 返回 %d 个候选, query='%s'",
        len(candidates), query_text[:50],
    )
    return candidates


def search_with_rewrite(user_query: str, filter_expr: str | None = None) -> list[dict]:
    """查询改写 + 混合检索的便捷封装"""
    rewritten = rewrite_query(user_query)
    query_vector = embed_single(rewritten)
    return hybrid_search(rewritten, query_vector, filter_expr=filter_expr)
