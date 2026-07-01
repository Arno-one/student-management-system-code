"""输入安全守卫 — 检测提示注入、越权、攻击性输入"""
import re
from agent_system.middleware.middleware_schema import MiddlewareResult
from util.log import get_logger

logger = get_logger(__name__)

# 提示注入特征
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|before)\s+(instructions?|prompts?|messages?)",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[system\]",
    r"\[/system\]",
    r"system\s*prompt",
    r"你是一个.*(?:忽略|忘记|不要).*",
    r"扮演.*角色",
    r"DAN\s*mode",
    r"jailbreak",
    r"从现在开始.*你是.*",
    r"忘记.*(?:规则|指令|限制|设定)",
]

_SENSITIVE_PATTERNS = [
    r"(?:drop|truncate|delete\s+from|insert\s+into|update\s+.*set)\s",
    r"(?:sudo|root|admin\s+access)",
    r"<script.*?>",
    r"\{\{.*?\}\}",
]

MAX_MESSAGE_LENGTH = 2000


def check(message: str) -> MiddlewareResult:
    """检测输入安全性，返回 pass 或 reject"""
    # 超长
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning("input_guard reject: 消息过长 (%s chars)", len(message))
        return MiddlewareResult(
            decision="reject", original_message=message,
            reject_reason=f"消息超过最大长度限制 ({MAX_MESSAGE_LENGTH}字符)",
        )

    # 空消息
    if not message.strip():
        return MiddlewareResult(
            decision="reject", original_message=message,
            reject_reason="消息不能为空",
        )

    lower = message.lower()

    # 注入检测
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, lower):
            logger.warning("input_guard reject: 检测到提示注入 pattern=%s", pat)
            return MiddlewareResult(
                decision="reject", original_message=message,
                reject_reason="输入包含不被允许的内容，请重新描述你的需求",
            )

    # 敏感操作
    for pat in _SENSITIVE_PATTERNS:
        if re.search(pat, lower):
            logger.warning("input_guard reject: 检测到敏感操作 pattern=%s", pat)
            return MiddlewareResult(
                decision="reject", original_message=message,
                reject_reason="输入包含不被允许的操作，请重新描述你的需求",
            )

    return MiddlewareResult(decision="pass", original_message=message)
