"""策略检查器 — 对中间件输出做最终安全校验"""
from agent_system.middleware.middleware_schema import MiddlewareResult
from util.log import get_logger

logger = get_logger(__name__)

# 改写后也不允许出现的关键词
_FORBIDDEN = [
    "忽略之前的指令",
    "ignore previous instructions",
    "你是 DAN",
    "越狱",
]


def check(original: str, rewritten: str | None) -> MiddlewareResult:
    """检查改写后的消息是否合规"""
    target = rewritten or original

    lower = target.lower()
    for word in _FORBIDDEN:
        if word.lower() in lower:
            logger.warning("policy_checker reject: 检测到禁止词 '%s'", word)
            return MiddlewareResult(
                decision="reject", original_message=original,
                rewritten_message=rewritten,
                reject_reason="输入包含不被允许的内容",
            )

    return MiddlewareResult(
        decision="pass" if rewritten is None else "rewrite",
        original_message=original,
        rewritten_message=rewritten,
    )
