"""
RAG 客户端统一初始化模块。

维护 Milvus、Embedding、LLM、CrossEncoder 各客户端的单例。
"""
from pymilvus import MilvusClient, connections
from openai import OpenAI
from dashscope import TextEmbedding

from RAG.config import config
from util.log import get_logger

logger = get_logger(__name__)

# ==================== Milvus ====================

_milvus_client: MilvusClient | None = None
_orm_connected: bool = False


def _ensure_orm_connection():
    """为 ORM 风格 API (Collection/Schema) 建立连接，MilvusClient 不共享此连接"""
    global _orm_connected
    if not _orm_connected:
        db_name = config.milvus_db_name
        connections.connect(
            alias="default",
            uri=config.milvus_uri,
            db_name=db_name,
        )
        _orm_connected = True
        logger.info("Milvus ORM 连接已建立: %s / %s", config.milvus_uri, db_name)


def get_milvus_client() -> MilvusClient:
    """获取 MilvusClient 单例，自动切换数据库"""
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient(uri=config.milvus_uri)
        _milvus_client.use_database(config.milvus_db_name)
        logger.info(
            "Milvus 已连接: %s, 数据库: %s",
            config.milvus_uri, config.milvus_db_name,
        )
        _ensure_orm_connection()
    return _milvus_client


# ==================== Embedding ====================

def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量文本 Embedding，返回向量列表"""
    if not texts:
        return []
    batch_size = config.embedding_batch_size
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = TextEmbedding.call(
            model=config.embedding_model,
            input=batch,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Embedding API 失败: {response.code} - {response.message}"
            )
        vectors = [item["embedding"] for item in response.output["embeddings"]]
        all_vectors.extend(vectors)
        logger.debug("Embedding batch %d/%d 完成", i // batch_size + 1, (len(texts) + batch_size - 1) // batch_size)
    return all_vectors


def embed_single(text: str) -> list[float]:
    """单条文本 Embedding"""
    return embed_texts([text])[0]


# ==================== LLM (DeepSeek) ====================

_llm_client: OpenAI | None = None


def get_llm_client() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )
        logger.info("LLM 客户端已初始化 (DeepSeek): %s", config.llm_base_url)
    return _llm_client


# ==================== CrossEncoder ====================

_reranker = None


def get_reranker():
    """懒加载 CrossEncoder，首次调用时下载/加载模型"""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info("正在加载 CrossEncoder 模型: %s", config.cross_encoder_model)
        _reranker = CrossEncoder(config.cross_encoder_model)
        logger.info("CrossEncoder 模型加载完成")
    return _reranker
