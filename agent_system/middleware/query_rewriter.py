"""查询改写器 — 模糊问题消歧，LLM 辅助指代消解"""
import re
from llm_basic import get_model
from langchain_core.messages import SystemMessage, HumanMessage
from agent_system.middleware.middleware_schema import MiddlewareResult
from util.log import get_logger

logger = get_logger(__name__)

# 模糊指代词 — 命中则触发 LLM 改写
_VAGUE_PATTERNS = [
    r"这个",
    r"那个",
    r"它[们]?",
    r"上面(的)?",
    r"刚才(的)?",
    r"之前(的)?",
    r"前面(的)?",
    r"上次(的)?",
    r"那个谁",
    r"帮我看下$",
    r"帮我看一下$",
    r"帮我查下$",
    r"帮我查一下$",
    r"怎么样$",
]

REWRITE_PROMPT = """你是一个问题改写助手。用户的问题可能包含指代不清的词语（如"这个""那个""上次的"），请结合对话历史将这些模糊表达改写为完整、清晰的问题。

改写规则（非常重要）：
1. 只允许补全、消歧、规范化，绝对不允许改变用户真实意图
2. 如果用户问题已经清晰完整，直接返回原句
3. 只输出改写后的一句话，不要任何解释
4. 如果无法从历史中确定指代内容，保持原句不变"""


def check(message: str, history: list | None = None, provider: str = "deepseek-v4") -> MiddlewareResult:
    """检测是否需要改写，需要时调 LLM"""
    # 快速规则判断
    needs_rewrite = False
    for pat in _VAGUE_PATTERNS:
        if re.search(pat, message):
            needs_rewrite = True
            break

    if not needs_rewrite:
        logger.debug("查询改写: 无需改写，直接 pass")
        return MiddlewareResult(decision="pass", original_message=message)

    # 构建 LLM 上下文
    history_text = ""
    if history:
        recent = history[-6:]
        lines = []
        for h in recent:
            if h.get("role") == "user":
                role = "用户"
            elif h.get("role") == "summary":
                role = "摘要"
            else:
                role = "助手"
            content = str(h.get("content", ""))[:150]
            lines.append(f"{role}: {content}")
        history_text = "\n".join(lines)

    user_input = f"对话历史:\n{history_text}\n\n当前问题: {message}" if history_text else f"当前问题: {message}"

    try:
        model = get_model(provider)
        msgs = [SystemMessage(content=REWRITE_PROMPT), HumanMessage(content=user_input)]
        response = model.invoke(msgs)
        rewritten = response.content.strip()

        # 如果 LLM 返回内容异常（太长或为空），保持原句
        if not rewritten or len(rewritten) > len(message) * 3:
            logger.warning("查询改写结果异常: len=%s, fallback to original", len(rewritten) if rewritten else 0)
            return MiddlewareResult(decision="pass", original_message=message)

        if rewritten == message:
            logger.debug("查询改写: LLM 判断无需改写")
            return MiddlewareResult(decision="pass", original_message=message)

        logger.info("查询改写: '%s' → '%s'", message[:60], rewritten[:80])
        return MiddlewareResult(decision="rewrite", original_message=message, rewritten_message=rewritten)

    except Exception as e:
        logger.exception("查询改写 LLM 调用失败: %s", e)
        return MiddlewareResult(decision="pass", original_message=message)
