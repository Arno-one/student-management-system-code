"""
Milvus Collection Schema 定义与创建。

在 four_novels_rag 数据库中创建 document_chunks 集合，
包含稠密向量(1024维) + BM25 稀疏向量 + 标量字段。
"""
from pymilvus import (
    Collection, CollectionSchema, FieldSchema,
    DataType, Function, FunctionType,
    connections, utility,
)
from RAG.config import config
from RAG.clients import get_milvus_client, _ensure_orm_connection
from util.log import get_logger

logger = get_logger(__name__)


def get_or_create_collection(drop_existing: bool = False) -> Collection:
    """
    获取或创建 document_chunks Collection。

    Args:
        drop_existing: 开发阶段可传 True 重建，生产环境传 False
    """
    _ensure_orm_connection()
    client = get_milvus_client()
    collection_name = config.milvus_collection_name

    # 如果已存在
    if client.has_collection(collection_name):
        if drop_existing:
            logger.warning("删除已有 Collection: %s", collection_name)
            client.drop_collection(collection_name)
        else:
            logger.info("Collection '%s' 已存在，复用", collection_name)
            # 用 ORM-style Collection 对象方便后续操作(load/search)
            return Collection(collection_name)

    # ---- 定义字段 ----
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
        # text: 文档切片原文 或 QA 合并搜索文本，BM25 索引在此字段
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4000,
                    enable_analyzer=True, enable_match=True),
        # QA 专用字段（文档切片时为空串）
        FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="answer", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="reason", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="chunk_index", dtype=DataType.INT32),
        FieldSchema(name="total_chunks", dtype=DataType.INT32),
        FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="created_at", dtype=DataType.INT64),
        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=config.embedding_dimension),
        FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
    ]

    schema = CollectionSchema(fields=fields, description="四大名著知识库 - 文档切片 + QA 问答对")
    schema.add_function(
        Function(
            name="text_bm25",
            input_field_names=["text"],
            output_field_names=["sparse_vector"],
            function_type=FunctionType.BM25,
        )
    )

    # ---- 创建 Collection ----
    collection = Collection(name=collection_name, schema=schema)
    logger.info("Collection '%s' 创建成功", collection_name)

    # ---- 建索引 ----
    _create_indexes(collection)

    return collection


def _create_indexes(collection: Collection) -> None:
    """为 dense 和 sparse 向量字段创建索引"""
    collection_name = config.milvus_collection_name
    client = get_milvus_client()

    # 稠密向量：AUTOINDEX + COSINE
    dense_index_params = client.prepare_index_params()
    dense_index_params.add_index(
        field_name="dense_vector",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )
    client.create_index(collection_name, dense_index_params)
    logger.info("dense_vector 索引(AUTOINDEX/COSINE) 创建完成")

    # 稀疏向量：BM25 倒排索引
    sparse_index_params = client.prepare_index_params()
    sparse_index_params.add_index(
        field_name="sparse_vector",
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="BM25",
    )
    client.create_index(collection_name, sparse_index_params)
    logger.info("sparse_vector 索引(SPARSE_INVERTED_INDEX/BM25) 创建完成")


def load_collection(collection: Collection) -> None:
    """加载 Collection 到内存，建立可检索状态"""
    collection.load()
    logger.info("Collection '%s' 已加载到内存", collection.name)
