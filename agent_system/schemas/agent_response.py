"""Agent 响应模型"""
from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    tool_name: str
    status: str  # "success" | "error"
    summary: str | None = None


class AgentChatResponse(BaseModel):
    reply: str = Field(..., description="Agent 自然语言回复")
    intent: str = Field(..., description="识别到的用户意图")
    persona: str = Field("academic_mentor", description="使用的角色")
    tool_calls: list[ToolCallRecord] | None = Field(None, description="工具调用记录")
    sources: list[dict] | None = Field(None, description="知识来源引用")
    cards: list[dict] | None = Field(None, description="结构化卡片数据，如天气卡片")
    session_id: int = Field(..., description="会话ID")
    task_id: int | None = Field(None, description="关联的 AgentTask ID，用于任务级反馈")
