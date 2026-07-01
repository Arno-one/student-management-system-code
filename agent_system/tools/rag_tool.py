"""RAG 知识检索工具 — FAQ 精确匹配 + RAG 向量检索"""
import re
from dataclasses import dataclass, field
from langchain_core.tools import tool

from agent_system.tools.base import BaseTool, ToolContext
from RAG.retrieval_service import search_context as _rag_search
from util.log import get_logger

logger = get_logger(__name__)


class RagTool(BaseTool):
    name = "rag_tool"
    description = "从知识库检索相关内容（学校制度、系统使用说明、名著知识），优先 FAQ 精确匹配"
    inputs_schema = {"question": str}

    def run(self, ctx: ToolContext) -> dict:
        question = ctx.params.get("question", "")
        return _search_knowledge(question)


# ==================== 校务 FAQ（精确匹配，不走 RAG） ====================

@dataclass
class _FaqEntry:
    keywords: list[str]       # 触发关键词
    patterns: list[str]       # 正则 pattern（可选）
    answer: str               # 预设回答


@dataclass
class _SchoolFaq:
    faq: _FaqEntry | None = None
    entries: list[_FaqEntry] = field(default_factory=list)

    def __post_init__(self):
        self.entries = [
            _FaqEntry(
                keywords=["请假", "怎么请假", "请假流程", "请假申请"],
                patterns=["请假"],
                answer=(
                    "关于请假功能：\n\n"
                    "当前版本的学生管理系统暂未包含在线请假/考勤模块。"
                    "如果你需要请假，建议通过以下方式处理：\n"
                    "1. 直接联系你的班主任或辅导员，按学校现行规定提交纸质或线下请假申请。\n"
                    "2. 如需学校层面的请假流程指引，请咨询班主任或教务处获取最新说明。\n\n"
                    "后续系统版本可能会新增考勤管理功能，届时会在系统公告中通知。"
                ),
            ),
            _FaqEntry(
                keywords=["成绩查询", "查成绩", "怎么看成绩", "怎么查成绩", "成绩在哪"],
                patterns=["查.*成绩", "成绩.*[查看]"],
                answer=(
                    "查询成绩的方法：\n\n"
                    "1. 登录学生管理系统，进入首页。\n"
                    "2. 在侧边栏找到「考核成绩管理」模块（/score），点击进入。\n"
                    "3. 在成绩管理页面，可以通过学号、考试序次、班级等条件筛选查看成绩记录。\n"
                    "4. 查询结果会显示学号、姓名、考试序次和分数。\n"
                    "5. 你也可以直接在「智能 Agent 助手」页面输入「帮我查一下我的成绩」，"
                    "Agent 会自动帮你查询并解释成绩情况。\n\n"
                    "注意：成绩数据由教师录入，如果你发现成绩缺失，请联系任课教师确认是否已录入。"
                ),
            ),
            _FaqEntry(
                keywords=["管理员", "admin", "默认密码", "管理员账号"],
                patterns=["管理员.*账号", "admin"],
                answer=(
                    "系统预置管理员账号为 admin，初始密码由系统部署时在环境变量中配置。\n"
                    "首次登录后建议立即修改密码以提高安全性。\n\n"
                    "管理员拥有系统最高权限，可以进行：\n"
                    "- 创建、编辑、禁用用户账号\n"
                    "- 分配用户角色和权限\n"
                    "- 查看和管理所有模块数据\n"
                    "- 系统配置和维护\n\n"
                    "如果你不是管理员，请联系管理员协助处理需要高级权限的操作。"
                ),
            ),
            _FaqEntry(
                keywords=["修改密码", "改密码", "怎么改密码", "密码忘了"],
                patterns=["修改.*密码", "改密码"],
                answer=(
                    "修改密码的方法：\n\n"
                    "1. 系统提供修改密码的 API 接口（POST /auth/change-password），"
                    "需要提供原密码和新密码，提交后立即生效。\n"
                    "2. 前端页面暂未设置独立的个人中心入口，如需修改密码，"
                    "可联系管理员协助，或在 API 文档（Swagger UI）中直接调用接口。\n"
                    "3. 如果你忘记了密码，请联系系统管理员进行密码重置。\n"
                    "4. 管理员可在「系统管理」模块（/system）中为用户重置密码。\n\n"
                    "安全提醒：请妥善保管个人密码，不要转借他人使用。"
                ),
            ),
            _FaqEntry(
                keywords=["登录", "怎么登录", "账号", "登录方式", "怎么进去"],
                patterns=["登录"],
                answer=(
                    "系统登录方式：\n\n"
                    "1. 打开系统网址（由学校或管理员提供），进入登录页面。\n"
                    "2. 输入你的账号（学生账号为本人学号）和密码。\n"
                    "3. 初始密码由管理员统一分配，首次登录后建议立即修改密码。\n"
                    "4. 点击「登录」按钮完成身份验证，进入系统首页。\n"
                    "5. 首页展示当前用户有权访问的功能模块。\n\n"
                    "如果登录时提示「账号已失效」，请联系管理员确认账号状态。"
                ),
            ),
            _FaqEntry(
                keywords=["删除", "逻辑删除", "恢复", "怎么恢复", "数据刪除"],
                patterns=["删除", "恢复", "逻辑删除"],
                answer=(
                    "关于数据删除：\n\n"
                    "系统中大部分模块（学生、成绩、就业、班级、教师）采用「逻辑删除」机制。\n"
                    "逻辑删除后数据仍然保留在数据库中，只是标记为已删除状态，"
                    "管理员可以在需要时恢复数据。\n"
                    "物理删除为不可逆操作，仅管理员可执行，会永久清除数据。\n\n"
                    "如果你误删了某条记录，请联系管理员协助恢复。"
                ),
            ),
            _FaqEntry(
                keywords=["NL2SQL", "智能问数", "自然语言查询", "怎么用NL2SQL"],
                patterns=["NL2SQL", "智能问数", "自然语言.*查"],
                answer=(
                    "NL2SQL 智能问数功能说明：\n\n"
                    "NL2SQL 让你可以用日常口语化的中文查询数据库，不需要手动筛选。\n"
                    "使用方法：\n"
                    "1. 在侧边栏点击「NL2SQL 智能问数」进入页面。\n"
                    "2. 在输入框中输入自然语言问题，如「张三的平均成绩是多少」「统计每个班级的人数」。\n"
                    "3. 系统会自动将问题转为 SQL 语句执行并返回结果。\n\n"
                    "安全机制：\n"
                    "- 所有生成的 SQL 都会经过安全校验，仅允许 SELECT 查询\n"
                    "- 使用只读数据库账号执行，不会修改数据\n"
                    "- 查询记录自动留存用于审计"
                ),
            ),
            _FaqEntry(
                keywords=["权限", "RBAC", "角色", "权限控制", "谁能用"],
                patterns=["权限", "RBAC", "角色"],
                answer=(
                    "系统权限说明：\n\n"
                    "系统采用 RBAC（基于角色的访问控制）模型，分三层：用户 → 角色 → 权限。\n"
                    "- 每个用户可拥有多个角色（如 admin、teacher、student）。\n"
                    "- 每个角色关联一组权限编码（如 student:view 表示查看学生信息的权限）。\n"
                    "- 你登录后能看到的模块和能执行的操作，由管理员分配的角色决定。\n\n"
                    "常见权限举例：\n"
                    "- student:view — 查看学生信息\n"
                    "- score:view — 查看成绩\n"
                    "- nl2sql:use — 使用智能问数\n"
                    "- work:use — 使用 AI 作业模块\n\n"
                    "如果你看不到某个模块，说明你的角色没有对应权限，请联系管理员。"
                ),
            ),
            _FaqEntry(
                keywords=["自然语言录入", "智能录入", "NL录入", "提取"],
                patterns=["自然语言.*录入", "智能.*录入", "自动.*填"],
                answer=(
                    "自然语言智能录入功能说明：\n\n"
                    "学生、成绩、就业三个模块均支持自然语言智能录入。\n"
                    "你只需要用日常语言描述信息，系统会通过大模型自动提取关键字段。\n\n"
                    "使用示例：\n"
                    "- 学生录入：「新增学生张三，学号S2024001，班级3班，男，20岁，计算机专业本科」\n"
                    "- 成绩录入：「学生S2025001第1次考试成绩85分」\n"
                    "- 就业录入：「学生S2024001，公司腾讯，薪资15000」\n\n"
                    "提取结果会展示在预览区让你确认和补填，确认无误后再提交。"
                ),
            ),
            _FaqEntry(
                keywords=["模块", "有哪些功能", "系统功能"],
                patterns=["哪些.*模块", "有什么.*功能", "功能.*模块"],
                answer=(
                    "本系统目前包含以下功能模块：\n\n"
                    "| 学生信息管理 | /student | 档案录入、查询、导入导出 |\n"
                    "| 考核成绩管理 | /score | 成绩录入、批量导入、多条件查询 |\n"
                    "| 班级管理 | /class | 班级创建、修改、删除 |\n"
                    "| 教师管理 | /teacher | 教师档案、导入导出 |\n"
                    "| 就业信息管理 | /Employment | 就业跟踪、offer记录 |\n"
                    "| 统计分析 | /statistics | 年龄分布、成绩筛选等聚合查询 |\n"
                    "| AI 作业模块 | /work | 评价生成、文生图、天气、多轮对话 |\n"
                    "| 邮件管理 | /email | AI 生成并发送邮件 |\n"
                    "| NL2SQL 智能问数 | /nl2sql | 自然语言转 SQL 查询 |\n"
                    "| 四大名著知识库 | /rag | RAG 检索 + AI 问答 |\n"
                    "| 智能 Agent 助手 | /agent | 学业导师、成绩查询、陪伴对话 |\n"
                    "| 系统管理 | /system | 用户、角色、权限管理 |\n\n"
                    "每个模块的可见性取决于你的角色权限。"
                ),
            ),
            _FaqEntry(
                keywords=["作业", "交作业", "查作业", "作业模块", "AI作业"],
                patterns=["作业"],
                answer=(
                    "AI 作业模块功能说明：\n\n"
                    "作业模块集成多项大模型驱动的智能能力：\n"
                    "1. 学生评价生成：根据学生信息自动生成个性化评价，"
                    "支持幽默、严肃、激励、批判四种风格。\n"
                    "2. 文生图：调用阿里云通义万相，根据文字描述生成图片。\n"
                    "3. 天气查询：集成腾讯地图 API，查询实时天气和多日预报。\n"
                    "4. 多轮对话：支持创建会话进行多轮 AI 对话，系统自动维护上下文。\n\n"
                    "入口：侧边栏「AI 作业模块」（/work）。"
                ),
            ),
            _FaqEntry(
                keywords=["就业", "offer", "薪资", "公司", "就业信息"],
                patterns=["就业", "offer", "公司.*薪资"],
                answer=(
                    "就业信息管理功能说明：\n\n"
                    "就业模块用于跟踪学生毕业就业去向，记录的信息包括：\n"
                    "- 学号、学生姓名、班级\n"
                    "- 就业开放时间、offer 下发时间\n"
                    "- 公司名称、薪资\n\n"
                    "支持单条创建、修改、分页查询（可按姓名/班级/公司名筛选）、"
                    "逻辑删除和恢复。\n"
                    "同样支持自然语言智能提取录入。\n\n"
                    "入口：侧边栏「就业信息管理」（/Employment）。"
                ),
            ),
        ]

    def search(self, question: str) -> str | None:
        """
        关键词匹配 FAQ，命中则返回预设答案，未命中返回 None。
        优先正则匹配，其次关键词包含匹配。
        """
        q = question.strip()
        for entry in self.entries:
            for pat in entry.patterns:
                if re.search(pat, q):
                    logger.info("FAQ 正则命中: pattern='%s', question='%s'", pat, q[:60])
                    return entry.answer
            for kw in entry.keywords:
                if kw in q:
                    logger.info("FAQ 关键词命中: keyword='%s', question='%s'", kw, q[:60])
                    return entry.answer
        return None


# 全局单例
_school_faq = _SchoolFaq()


# ==================== 工具定义 ====================


@tool
def search_knowledge(question: str) -> dict:
    """
    从知识库中检索相关内容片段（学校制度、系统使用说明、名著知识）。
    优先走校务 FAQ 精确匹配，未命中再走 RAG 向量检索。

    Args:
        question: 要检索的问题
    """
    pass


def _search_knowledge(question: str) -> dict:
    """
    内部实现：FAQ 优先 → RAG 兜底。
    先尝试 FAQ 关键词/正则匹配，命中直接返回预设答案；
    未命中则走 Milvus 向量检索。
    """
    # 1. 先查 FAQ
    faq_answer = _school_faq.search(question)
    if faq_answer:
        return {
            "success": True,
            "question": question,
            "rewritten_query": question,
            "chunks": [{
                "source_id": "school_faq",
                "file_name": "校务FAQ",
                "text": faq_answer,
                "text_preview": faq_answer[:120],
                "source_type": "faq",
                "score": 1.0,
            }],
            "total": 1,
            "faq_hit": True,
            "error": None,
        }

    # 2. FAQ 未命中，走 RAG 向量检索
    try:
        result = _rag_search(question, enable_rerank=True)

        chunks = []
        for c in result.chunks:
            chunks.append({
                "source_id": c.source_id,
                "file_name": c.file_name,
                "text": c.text,
                "text_preview": c.text_preview,
                "source_type": c.source_type,
                "score": c.score,
            })

        logger.info("RAG 检索成功: question='%s', chunks=%s", question[:60], len(chunks))
        return {
            "success": True,
            "question": result.question,
            "rewritten_query": result.rewritten_query,
            "chunks": chunks,
            "total": len(chunks),
            "faq_hit": False,
            "error": None,
        }
    except Exception as e:
        logger.exception("RAG 检索异常: question='%s', %s", question[:60], e)
        return {
            "success": False,
            "chunks": [],
            "total": 0,
            "faq_hit": False,
            "error": f"知识检索失败: {e}",
        }
