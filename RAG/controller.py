"""
RAG FastAPI 接口层。

兼容旧接口：
- /rag/ask
- /rag/ingest

新增通用多知识库接口：
- /rag/kbs/{kb_id}/ask
- /rag/kbs/{kb_id}/ingest
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from RAG.ask_service import ask_question
from RAG.config import config
from RAG.ingestion import ingest_documents
from util.log import get_logger

logger = get_logger(__name__)

rag_router = APIRouter()


class AskRequest(BaseModel):
    """问答请求体。"""

    question: str = Field(..., description="用户问题", min_length=1, max_length=500)
    enable_rerank: bool | None = Field(None, description="是否启用精排，None 使用默认配置")
    top_k: int | None = Field(None, description="返回候选数，None 使用默认配置")


class IngestRequest(BaseModel):
    """入库请求体。"""

    drop_existing: bool = Field(False, description="是否删除已有数据后重新入库")
    max_chapters: int | None = Field(None, description="每本书最多处理回数，仅 novels 知识库生效")


class AskData(BaseModel):
    """问答响应核心数据。"""

    question: str
    rewritten_query: str | None
    answer: str
    citations: list[dict]
    trace: dict


@rag_router.post("/ask")
async def ask(request: AskRequest):
    """兼容旧接口，默认走 novels 知识库。"""
    return await ask_by_kb(config.default_kb_id, request)


@rag_router.post("/kbs/{kb_id}/ask")
async def ask_by_kb(kb_id: str, request: AskRequest):
    """多知识库问答接口。"""
    try:
        result = ask_question(
            question=request.question,
            kb_id=kb_id,
            enable_rerank=request.enable_rerank,
            top_k=request.top_k,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[%s] 问答失败", kb_id)
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc

    data = AskData(
        question=result["question"],
        rewritten_query=result.get("rewritten_query"),
        answer=result["answer"],
        citations=result["citations"],
        trace=result["trace"],
    )
    return {"code": 200, "msg": "success", "data": data.model_dump(), "total": None}


@rag_router.post("/ingest")
async def ingest(request: IngestRequest):
    """兼容旧接口，默认走 novels 知识库。"""
    return await ingest_by_kb(config.default_kb_id, request)


@rag_router.post("/kbs/{kb_id}/ingest")
async def ingest_by_kb(kb_id: str, request: IngestRequest):
    """多知识库入库接口。"""
    try:
        with config.use_kb(kb_id):
            logger.info("[%s] 收到入库请求: drop_existing=%s, max_chapters=%s", kb_id, request.drop_existing, request.max_chapters)
            original_max_chapters = config.max_chapters
            if request.max_chapters is not None:
                config.max_chapters = request.max_chapters

            try:
                result = ingest_documents(drop_existing=request.drop_existing)
            finally:
                config.max_chapters = original_max_chapters

            return {"code": 200, "msg": "入库完成", "data": result, "total": result["total_chunks"]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[%s] 入库失败", kb_id)
        raise HTTPException(status_code=500, detail=f"入库失败: {exc}") from exc


@rag_router.get("/status")
async def status():
    """兼容旧接口，默认查询 novels。"""
    return await status_by_kb(config.default_kb_id)


@rag_router.get("/kbs/{kb_id}/status")
async def status_by_kb(kb_id: str):
    """多知识库状态接口。"""
    from RAG.clients import get_milvus_client

    try:
        with config.use_kb(kb_id):
            client = get_milvus_client()
            collection_name = config.milvus_collection_name
            if not client.has_collection(collection_name):
                return {
                    "code": 200,
                    "msg": "知识库未初始化",
                    "data": {
                        "kb_id": kb_id,
                        "collection_name": collection_name,
                        "total_chunks": 0,
                        "files": [],
                        "config_summary": _config_summary(),
                    },
                    "total": 0,
                }

            try:
                stats = client.get_collection_stats(collection_name)
                row_count = stats.get("row_count", 0)
            except Exception:
                row_count = -1

            try:
                rows = client.query(
                    collection_name=collection_name,
                    filter="id >= 0",
                    output_fields=["file_name"],
                    limit=10000,
                )
                files = list({row["file_name"] for row in rows})
            except Exception:
                files = []

            return {
                "code": 200,
                "msg": "success",
                "data": {
                    "kb_id": kb_id,
                    "collection_name": collection_name,
                    "total_chunks": row_count,
                    "files": files,
                    "config_summary": _config_summary(),
                },
                "total": row_count,
            }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@rag_router.get("/health")
async def health():
    """基础健康检查。"""
    checks = {}

    try:
        from RAG.clients import get_milvus_client

        get_milvus_client().list_collections()
        checks["milvus"] = "OK"
    except Exception as exc:
        checks["milvus"] = f"FAIL: {exc}"

    try:
        from RAG.clients import embed_single

        embed_single("测试")
        checks["embedding"] = "OK"
    except Exception as exc:
        checks["embedding"] = f"FAIL: {exc}"

    try:
        from RAG.clients import get_llm_client

        llm = get_llm_client()
        llm.chat.completions.create(
            model=config.llm_rewrite_model,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10,
        )
        checks["llm"] = "OK"
    except Exception as exc:
        checks["llm"] = f"FAIL: {exc}"

    if config.enable_rerank:
        try:
            from RAG.clients import get_reranker

            get_reranker()
            checks["cross_encoder"] = "OK"
        except Exception as exc:
            checks["cross_encoder"] = f"FAIL: {exc}"
    else:
        checks["cross_encoder"] = "disabled"

    all_ok = all(
        status == "OK"
        for name, status in checks.items()
        if name != "cross_encoder" or config.enable_rerank
    )
    return {
        "code": 200 if all_ok else 503,
        "msg": "所有组件正常" if all_ok else "部分组件异常",
        "data": checks,
        "total": None,
    }


def _config_summary() -> dict:
    """统一返回当前知识库的配置摘要，便于排查。"""
    return {
        "kb_id": config.active_kb_id,
        "collection_name": config.milvus_collection_name,
        "docs_dir": str(config.docs_dir),
        "embedding_model": config.embedding_model,
        "embedding_dimension": config.embedding_dimension,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "max_chapters": config.max_chapters,
        "enable_rerank": config.enable_rerank,
        "llm_rewrite_model": config.llm_rewrite_model,
        "llm_generate_model": config.llm_generate_model,
    }
