"""Agent 工作记忆 — 管理当前任务需要的短上下文。"""
import json
from typing import Any

from model.Talk import TalkMessage


def message_to_history_item(message: TalkMessage) -> dict[str, str] | None:
    """把数据库消息转换成 LLM 可读的历史项。"""
    if message.role == "user" and message.user_content:
        return {"role": "user", "content": message.user_content}

    if message.role == "assistant" and message.ai_content:
        # assistant 内容可能是 {"reply": "...", ...metadata}，历史里只给自然语言回复。
        try:
            data = json.loads(message.ai_content)
            reply = data.get("reply", message.ai_content)
        except (json.JSONDecodeError, TypeError):
            reply = message.ai_content
        return {"role": "assistant", "content": str(reply)}

    return None


def build_recent_history(messages: list[TalkMessage], max_messages: int = 5) -> list[dict[str, str]]:
    """只保留最近 N 条原文，避免长对话无限塞进上下文。"""
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    history: list[dict[str, str]] = []
    for message in recent_messages:
        item = message_to_history_item(message)
        if item:
            history.append(item)
    return history


def build_context_history(summary: str | None, recent_history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """拼出“会话摘要 + 最近原文”的上下文结构。"""
    history: list[dict[str, str]] = []
    if summary:
        history.append({
            "role": "summary",
            "content": f"【会话摘要】{summary.strip()}",
        })
    history.extend(
        {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
        for item in recent_history
        if item.get("content")
    )
    return history


def estimate_history_chars(history: list[dict[str, Any]]) -> int:
    """粗略估算历史文本长度，用于触发摘要压缩。"""
    return sum(len(str(item.get("content", ""))) for item in history)
