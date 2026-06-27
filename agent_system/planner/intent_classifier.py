"""意图分类器 — 基于 LLM 结构化输出"""
from llm_basic import structured_complete
from agent_system.prompts.intent_prompt import INTENT_CLASSIFY_PROMPT, IntentResult
from util.log import get_logger

logger = get_logger(__name__)

# 意图分类失败时的兜底
_FALLBACK_INTENT = "general_chat"


def classify_intent(message: str, provider: str = "deepseek") -> dict:
    """
    识别用户消息的意图类型。

    Args:
        message: 用户输入的自然语言
        provider: LLM provider

    Returns:
        {"intent": "score_query", "confidence": 0.9}  或
        {"intent": "general_chat", "confidence": 0.0}  （降级）
    """
    result = structured_complete(
        system_prompt=INTENT_CLASSIFY_PROMPT,
        user_message=message,
        schema=IntentResult,
        provider=provider,
    )

    if result["error"] or result["parsed"] is None:
        logger.warning("意图分类失败，降级为 general_chat: %s", result.get("error"))
        return {"intent": _FALLBACK_INTENT, "confidence": 0.0}

    parsed = result["parsed"]
    logger.info("意图分类: '%s' → %s (confidence=%.2f)", message[:60], parsed.intent, parsed.confidence)
    return {"intent": parsed.intent, "confidence": parsed.confidence}
