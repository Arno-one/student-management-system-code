"""Agent 请求模型"""
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="用户消息", min_length=1, max_length=2000)
    session_id: int | None = Field(None, description="会话ID，不传则自动创建新会话")
    persona: str = Field("academic_mentor", description="角色标识")
    student_no: str | None = Field(None, description="目标学号，不传则自动从当前用户推导")
