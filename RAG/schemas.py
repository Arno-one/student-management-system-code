"""
Milvus Collection Schema 定义与创建。
"""
from __future__ import annotations

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, Function, FunctionType

from RAG.clients import _ensure_orm_connection, get_milvus_client
from RAG.config import config
from util.log import get_logger

logger = get_logger(__name__)


def get_or_create_collection(drop_existing: bool = False) -> Collection:
    """获取或创建当前知识库对应的 Collection。"""
    _ensure_orm_connection()
    client = get_milvus_client()
    collection_name = config.milvus_collection_name

    if client.has_collection(collection_name):
        if drop_existing:
            logger.warning("[%s] 删除已有 Collection: %s", config.active_kb_id, collection_name)
            client.drop_collection(collection_name)
        else:
            logger.info("[%s] Collection '%s' 已存在，直接复用", config.active_kb_id, collection_name)
            return Collection(collection_name)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=4000,
            enable_analyzer=True,
            enable_match=True,
        ),
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

    schema = CollectionSchema(fields=fields, description=config.current_kb.collection_description)
    schema.add_function(
        Function(
            name="text_bm25",
            input_field_names=["text"],
            output_field_names=["sparse_vector"],
            function_type=FunctionType.BM25,
        )
    )

    collection = Collection(name=collection_name, schema=schema)
    logger.info("[%s] Collection '%s' 创建成功", config.active_kb_id, collection_name)
    _create_indexes(collection_name)
    return collection


def _create_indexes(collection_name: str) -> None:
    """为当前 Collection 创建 dense 和 sparse 索引。"""
    client = get_milvus_client()

    dense_index_params = client.prepare_index_params()
    dense_index_params.add_index(field_name="dense_vector", index_type="AUTOINDEX", metric_type="COSINE")
    client.create_index(collection_name, dense_index_params)
    logger.info("[%s] dense_vector 索引创建完成", config.active_kb_id)

    sparse_index_params = client.prepare_index_params()
    sparse_index_params.add_index(
        field_name="sparse_vector",
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="BM25",
    )
    client.create_index(collection_name, sparse_index_params)
    logger.info("[%s] sparse_vector 索引创建完成", config.active_kb_id)


def load_collection(collection: Collection) -> None:
    """把 Collection 加载进内存，确保检索链路可用。"""
    collection.load()
    logger.info("[%s] Collection '%s' 已加载到内存", config.active_kb_id, collection.name)
