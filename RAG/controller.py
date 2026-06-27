"""
RAG 知识库 FastAPI 接口层。

提供对前端展示调用的标准 API。
响应格式与项目保持一致: {code, msg, data, total}
"""
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from RAG.retrieval_service import search_context
from RAG.prompt_builder import build_prompt
from RAG.generation import generate_answer
from RAG.config import config
from util.log import get_logger

logger = get_logger(__name__)

rag_router = APIRouter()

# ==================== 请求/响应模型 ====================


class AskRequest(BaseModel):
    question: str = Field(..., description="用户问题", min_length=1, max_length=500)
    enable_rerank: bool | None = Field(None, description="是否启用精排，None 使用默认配置")
    top_k: int | None = Field(None, description="返回候选数，None 使用默认配置")


class IngestRequest(BaseModel):
    drop_existing: bool = Field(False, description="是否删除已有数据后重新入库")
    max_chapters: int | None = Field(None, description="每本书最多处理回数，None=使用配置默认")


class StatusResponse(BaseModel):
    collection_name: str
    total_chunks: int
    files: list[str]
    config_summary: dict


class AskData(BaseModel):
    question: str
    rewritten_query: str | None
    answer: str
    citations: list[dict]
    trace: dict


# ==================== API ====================


@rag_router.post("/ask")
async def ask(request: AskRequest):
    """单次 RAG 问答"""
    t_start = time.time()
    trace = {}

    # --- 1. 检索（复用 retrieval_service） ---
    enable_rerank = request.enable_rerank if request.enable_rerank is not None else config.enable_rerank
    retrieval = search_context(request.question, enable_rerank=enable_rerank)

    trace["rewrite_ms"] = retrieval.retrieval_ms  # 检索阶段含改写
    trace["candidate_count"] = len(retrieval.chunks)
    trace["final_count"] = len(retrieval.chunks)
    logger.info("[RAG] 检索完成 | 改写='%s' | %d chunks | %dms",
                retrieval.rewritten_query, len(retrieval.chunks), retrieval.retrieval_ms)

    # --- 2. 转为 prompt_builder 需要的候选格式 ---
    candidates = [
        {
            "doc_id": c.source_id,
            "file_name": c.file_name,
            "chunk_index": c.chunk_index,
            "text": c.text,
            "source_type": c.source_type,
            "rerank_score": c.score,
        }
        for c in retrieval.chunks
    ]

    # --- 3. Prompt 组装 ---
    t0 = time.time()
    prompt = build_prompt(request.question, candidates)
    trace["prompt_ms"] = round((time.time() - t0) * 1000, 1)
    trace["context_tokens"] = prompt["context_tokens"]
    trace["context_blocks"] = len(prompt["context_blocks"])

    # --- 4. LLM 生成 ---
    result = generate_answer(
        user_query=request.question,
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        citations=prompt["citations"],
    )

    trace["generate_ms"] = result["generate_ms"]
    trace["total_ms"] = round((time.time() - t_start) * 1000, 1)
    trace["fallback"] = result["fallback"]

    data = AskData(
        question=request.question,
        rewritten_query=retrieval.rewritten_query if retrieval.rewritten_query != request.question else None,
        answer=result["answer"],
        citations=result["citations"],
        trace=trace,
    )

    logger.info(
        "[RAG] 问答完成 | Q='%s' | 检索=%dms 组装=%.0fms 生成=%.0fms | 总计=%.0fms | fallback=%s",
        request.question[:60], retrieval.retrieval_ms,
        trace["prompt_ms"], trace["generate_ms"], trace["total_ms"], result["fallback"],
    )

    return {"code": 200, "msg": "success", "data": data.model_dump(), "total": None}


@rag_router.post("/ingest")
async def ingest(request: IngestRequest):
    """触发文档入库"""
    from RAG.ingestion import ingest_documents

    logger.info("收到入库请求: drop_existing=%s, max_chapters=%s",
                request.drop_existing, request.max_chapters)

    # 临时覆盖配置
    if request.max_chapters is not None:
        config.max_chapters = request.max_chapters

    try:
        result = ingest_documents(drop_existing=request.drop_existing)
        return {"code": 200, "msg": "入库完成", "data": result, "total": result["total_chunks"]}
    except Exception as e:
        logger.exception("入库失败")
        raise HTTPException(status_code=500, detail=f"入库失败: {e}")


@rag_router.get("/status")
async def status():
    """查询知识库状态"""
    from RAG.clients import get_milvus_client
    client = get_milvus_client()

    collection_name = config.milvus_collection_name
    if not client.has_collection(collection_name):
        return {
            "code": 200,
            "msg": "知识库未初始化",
            "data": {"collection_name": collection_name, "total_chunks": 0, "files": [], "config_summary": _config_summary()},
            "total": 0,
        }

    # 获取 chunk 总数
    try:
        stats = client.get_collection_stats(collection_name)
        row_count = stats.get("row_count", 0)
    except Exception:
        row_count = -1

    # 获取文件列表
    try:
        results = client.query(
            collection_name=collection_name,
            filter="id >= 0",
            output_fields=["file_name"],
            limit=10000,
        )
        files = list({r["file_name"] for r in results})
    except Exception:
        files = []

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "collection_name": collection_name,
            "total_chunks": row_count,
            "files": files,
            "config_summary": _config_summary(),
        },
        "total": row_count,
    }


@rag_router.get("/health")
async def health():
    """健康检查：检测各组件联通性"""
    checks = {}

    # Milvus
    try:
        from RAG.clients import get_milvus_client
        client = get_milvus_client()
        client.list_collections()
        checks["milvus"] = "OK"
    except Exception as e:
        checks["milvus"] = f"FAIL: {e}"

    # Embedding
    try:
        from RAG.clients import embed_single
        embed_single("测试")
        checks["embedding"] = "OK"
    except Exception as e:
        checks["embedding"] = f"FAIL: {e}"

    # LLM
    try:
        from RAG.clients import get_llm_client
        llm = get_llm_client()
        llm.chat.completions.create(
            model=config.llm_rewrite_model,
            messages=[{"role": "user", "content": "1+1=?"}],
            max_tokens=10,
        )
        checks["llm"] = "OK"
    except Exception as e:
        checks["llm"] = f"FAIL: {e}"

    # CrossEncoder
    if config.enable_rerank:
        try:
            from RAG.clients import get_reranker
            get_reranker()
            checks["cross_encoder"] = "OK"
        except Exception as e:
            checks["cross_encoder"] = f"FAIL: {e}"
    else:
        checks["cross_encoder"] = "disabled"

    all_ok = all(v == "OK" for k, v in checks.items() if k != "cross_encoder" or config.enable_rerank)

    return {
        "code": 200 if all_ok else 503,
        "msg": "所有组件正常" if all_ok else "部分组件异常",
        "data": checks,
        "total": None,
    }


def _config_summary() -> dict:
    return {
        "embedding_model": config.embedding_model,
        "embedding_dimension": config.embedding_dimension,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "max_chapters": config.max_chapters,
        "enable_rerank": config.enable_rerank,
        "llm_rewrite_model": config.llm_rewrite_model,
        "llm_generate_model": config.llm_generate_model,
    }
