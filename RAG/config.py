"""
RAG 知识库统一配置模块。

这里除了保存通用运行参数外，还维护多知识库配置表。
当前至少包含两套知识库：
1. novels: 现有四大名著知识库
2. production: 新增的工程文档知识库
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

load_dotenv()

# DashScope SDK 强依赖 DASHSCOPE_API_KEY，这里从项目统一的阿里云 Key 映射过去。
_aliyun_key = os.getenv("ALIYUN_API_KEY", "")
if _aliyun_key and not os.getenv("DASHSCOPE_API_KEY"):
    os.environ["DASHSCOPE_API_KEY"] = _aliyun_key

_BASE_DIR = Path(__file__).resolve().parent
_active_kb_id: ContextVar[str] = ContextVar("rag_active_kb_id", default="novels")


@dataclass(frozen=True)
class KnowledgeBaseConfig:
    """单个知识库的静态配置。"""

    kb_id: str
    name: str
    collection_name: str
    docs_dir: Path
    collection_description: str
    rewrite_system_prompt: str
    answer_system_prompt: str
    eval_file: Path | None = None
    supported_extensions: tuple[str, ...] = (".md",)
    qa_direct_enabled: bool = False
    qa_direct_threshold: float = 0.78
    qa_margin_threshold: float = 0.08
    retrieval_min_score: float = 0.20
    refuse_when_insufficient: bool = False


def _build_kb_configs() -> dict[str, KnowledgeBaseConfig]:
    """集中构建知识库配置表，后续新增知识库时只需要在这里补一条。"""
    return {
        "novels": KnowledgeBaseConfig(
            kb_id="novels",
            name="四大名著知识库",
            collection_name="document_chunks",
            docs_dir=_BASE_DIR / "docs",
            collection_description="四大名著知识库 - 文档切片 + QA 问答对",
            rewrite_system_prompt=(
                "你是搜索查询优化器。将用户的口语化问题改写为简洁、关键词密集的检索查询。"
                "保留所有专有名词。只输出改写后的查询，不要解释。"
                "如果用户问的是四大名著相关，保留人物名、地名、事件名等关键信息。"
            ),
            answer_system_prompt=(
                "你是一个四大名著知识问答助手。请严格基于下面提供的上下文信息回答问题。\n\n"
                "规则：\n"
                "1. 只能基于上下文回答，不要使用外部知识。\n"
                "2. 如果上下文不足以回答问题，请明确说「资料不足，无法确定」。\n"
                "3. 回答中引用来源编号，例如 [来源 1]。\n"
                "4. 不要编造文件名、页码或不存在的引用。\n"
                "5. 简洁准确，直接回答核心问题。"
            ),
            supported_extensions=(".md",),
            qa_direct_enabled=False,
            refuse_when_insufficient=False,
        ),
        "production": KnowledgeBaseConfig(
            kb_id="production",
            name="工程文档知识库",
            collection_name="production_document_chunks",
            docs_dir=_BASE_DIR / "docs" / "production",
            collection_description="工程文档知识库 - PDF/DOCX/Markdown 切片 + QA 问答对",
            rewrite_system_prompt=(
                "你是工程文档检索查询优化器。请把用户问题改写成适合工程初步设计文档检索的关键词查询。"
                "保留项目名称、容量、电压等级、机型、海缆、风资源、水文、土建、投资等专业术语。"
                "如果问题涉及表格、参数、时间、高度、单位，请保留这些限定信息。"
                "只输出改写后的查询，不要解释。"
            ),
            answer_system_prompt=(
                "你是一个工程设计文档问答助手。请严格基于提供的参考资料回答。\n\n"
                "规则：\n"
                "1. 只能依据资料内容作答，不要补充外部常识。\n"
                "2. 回答时尽量保留原文中的数值、单位、对象名称和限定条件。\n"
                "3. 如果资料不足以支持回答，请明确说「资料不足，无法确定」。\n"
                "4. 回答中引用来源编号，例如 [来源 1]。\n"
                "5. 不要编造来源、页码、参数或结论。\n"
                "6. 优先给出结论，再补充必要说明。"
            ),
            eval_file=_BASE_DIR / "docs" / "production" / "需求问题-评测集.json",
            supported_extensions=(".pdf", ".docx", ".md"),
            qa_direct_enabled=True,
            qa_direct_threshold=0.82,
            qa_margin_threshold=0.05,
            retrieval_min_score=0.15,
            refuse_when_insufficient=True,
        ),
    }


@dataclass
class RagConfig:
    """RAG 统一运行配置。通用参数在这里，知识库差异走 kb 配置表。"""

    # ---- 阿里云百炼 API（仅用于 Embedding） ----
    aliyun_api_key: str = field(default_factory=lambda: os.getenv("ALIYUN_API_KEY", ""))

    # ---- embedding 模型 ----
    embedding_model: str = "text-embedding-v3"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 10

    # ---- Milvus ----
    milvus_uri: str = field(default_factory=lambda: os.getenv("MILVUS_URI", "http://localhost:19530"))
    milvus_db_name: str = field(default_factory=lambda: os.getenv("RAG_MILVUS_DB", "four_novels_rag"))

    # ---- DeepSeek API ----
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )

    # ---- LLM (DeepSeek) ----
    llm_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    llm_rewrite_model: str = "deepseek-chat"
    llm_generate_model: str = "deepseek-chat"

    # ---- 文档切片 ----
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ---- 检索 ----
    hybrid_top_k: int = 10
    rrf_k: int = 60
    rrf_final_n: int = 10

    # ---- 精排 ----
    cross_encoder_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_k: int = 3
    enable_rerank: bool = True

    # ---- Token 预算 ----
    max_context_tokens: int = 2000

    # ---- 文档范围 ----
    max_chapters: int | None = 30

    # ---- 知识库配置 ----
    knowledge_bases: dict[str, KnowledgeBaseConfig] = field(default_factory=_build_kb_configs)
    default_kb_id: str = field(default_factory=lambda: os.getenv("RAG_DEFAULT_KB", "novels"))

    @property
    def is_configured(self) -> bool:
        return bool(self.aliyun_api_key and self.milvus_uri)

    def masked_key(self) -> str:
        """打印配置时不泄露完整 Key。"""
        if not self.aliyun_api_key:
            return "<未配置>"
        if len(self.aliyun_api_key) <= 20:
            return "***"
        return f"{self.aliyun_api_key[:12]}...{self.aliyun_api_key[-4:]}"

    def get_kb(self, kb_id: str | None = None) -> KnowledgeBaseConfig:
        """获取指定知识库配置，不传时取当前上下文中的活跃知识库。"""
        target_kb_id = kb_id or _active_kb_id.get()
        try:
            return self.knowledge_bases[target_kb_id]
        except KeyError as exc:
            supported = ", ".join(sorted(self.knowledge_bases))
            raise KeyError(f"未知知识库 kb_id='{target_kb_id}'，可选值: {supported}") from exc

    @property
    def active_kb_id(self) -> str:
        """当前上下文中的知识库 ID。"""
        return _active_kb_id.get()

    @property
    def current_kb(self) -> KnowledgeBaseConfig:
        """当前上下文中的知识库配置。"""
        return self.get_kb()

    @property
    def milvus_collection_name(self) -> str:
        """当前知识库对应的 Collection 名称。"""
        return self.current_kb.collection_name

    @property
    def docs_dir(self) -> Path:
        """当前知识库对应的文档目录。"""
        return self.current_kb.docs_dir

    @property
    def rewrite_system_prompt(self) -> str:
        """当前知识库的查询改写提示词。"""
        return self.current_kb.rewrite_system_prompt

    @property
    def answer_system_prompt(self) -> str:
        """当前知识库的回答系统提示词。"""
        return self.current_kb.answer_system_prompt

    @contextmanager
    def use_kb(self, kb_id: str) -> Iterator[KnowledgeBaseConfig]:
        """在当前上下文中临时切换知识库，避免全局变量互相污染。"""
        kb = self.get_kb(kb_id)
        token = _active_kb_id.set(kb.kb_id)
        try:
            yield kb
        finally:
            _active_kb_id.reset(token)


config = RagConfig()
