"""
RAG 知识库统一配置模块。

所有配置从项目 .env 读取，不硬编码密钥。其他模块统一从这里 import。
"""
import os
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# DashScope SDK 硬要求 DASHSCOPE_API_KEY 环境变量，这里从 .env 的 ALIYUN_API_KEY 映射过去
_aliyun_key = os.getenv("ALIYUN_API_KEY", "")
if _aliyun_key and not os.getenv("DASHSCOPE_API_KEY"):
    os.environ["DASHSCOPE_API_KEY"] = _aliyun_key


@dataclass
class RagConfig:
    """RAG 知识库统一配置，所有模块依赖此对象，不直接散落 os.getenv"""

    # ---- 阿里云百炼 API（仅用于 Embedding） ----
    aliyun_api_key: str = field(
        default_factory=lambda: os.getenv("ALIYUN_API_KEY", "")
    )

    # ---- embedding 模型 ----
    embedding_model: str = "text-embedding-v3"
    embedding_dimension: int = 1024          # text-embedding-v3 固定 1024 维
    embedding_batch_size: int = 10           # API 单次最多 10 条

    # ---- Milvus ----
    milvus_uri: str = field(
        default_factory=lambda: os.getenv("MILVUS_URI", "http://localhost:19530")
    )
    milvus_db_name: str = field(
        default_factory=lambda: os.getenv("RAG_MILVUS_DB", "four_novels_rag")
    )
    milvus_collection_name: str = "document_chunks"

    # ---- DeepSeek API ----
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )

    # ---- LLM (DeepSeek) ----
    llm_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    llm_rewrite_model: str = "deepseek-chat"     # 查询改写
    llm_generate_model: str = "deepseek-chat"  # 答案生成

    # ---- 文档切片 ----
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ---- 检索 ----
    hybrid_top_k: int = 10         # 混合检索每路返回数
    rrf_k: int = 60               # RRF 融合参数
    rrf_final_n: int = 10         # 融合后 Top-N 候选（送入精排）

    # ---- 精排 ----
    cross_encoder_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_k: int = 3          # 精排后最终返回数
    enable_rerank: bool = True     # 是否开启精排

    # ---- Token 预算 ----
    max_context_tokens: int = 2000

    # ---- 文档范围 ----
    max_chapters: int | None = 30  # 每本书最多处理回数，None=全部

    # ---- API Key 校验 ----
    @property
    def is_configured(self) -> bool:
        return bool(self.aliyun_api_key and self.milvus_uri)

    def masked_key(self) -> str:
        """打印配置时不泄露完整 Key"""
        k = self.aliyun_api_key
        if not k:
            return "<未配置>"
        return k[:12] + "..." + k[-4:] if len(k) > 20 else "***"


# 全局单例
config = RagConfig()
