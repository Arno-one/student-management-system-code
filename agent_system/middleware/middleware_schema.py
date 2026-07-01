"""中间件统一数据模型"""
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class MiddlewareResult:
    """中间件处理结果"""
    decision: Literal["pass", "rewrite", "reject", "clarification"]
    original_message: str
    rewritten_message: str | None = None
    reject_reason: str | None = None
    clarification_message: str | None = None
    metadata: dict = field(default_factory=dict)
