"""
CrossEncoder 精排模块：对 RRF 融合后的 Top-N 候选做二次精排。

延迟敏感场景可设置 enable_rerank=False 跳过。
"""
from RAG.config import config
from RAG.clients import get_reranker
from util.log import get_logger

logger = get_logger(__name__)


def rerank(query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
    """
    CrossEncoder 精排。

    对 (query, candidate_text) 逐对打分，按分数降序返回 Top-K。

    Args:
        query: 用户原始问题
        candidates: RRF 融合后的候选列表，每个候选含 "text" 等字段
        top_k: 精排后返回数量

    Returns:
        精排后的候选列表，每个候选新增 "rerank_score" 字段
    """
    if not config.enable_rerank:
        logger.debug("CrossEncoder 精排已关闭，直接返回 RRF 结果")
        return candidates[: (top_k or config.rerank_top_k)]

    top_k = top_k or config.rerank_top_k

    if not candidates:
        return []

    try:
        model = get_reranker()
        pairs = [[query, c["text"]] for c in candidates]
        scores = model.predict(pairs, show_progress_bar=False)

        # 将分数写入候选
        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)

        # 按分数降序
        ranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        result = ranked[:top_k]

        logger.info(
            "CrossEncoder 精排: %d → %d, top_score=%.3f",
            len(candidates), len(result),
            result[0]["rerank_score"] if result else 0,
        )
        return result

    except Exception as e:
        logger.warning("CrossEncoder 精排失败，降级为 RRF Top-K: %s", e)
        return candidates[:top_k]
