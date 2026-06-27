"""HITL 数据模型"""
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
import time


@dataclass
class HitlState:
    """暂停时的执行状态"""
    tool_name: str
    preview: dict = field(default_factory=dict)
    paused_at: float = field(default_factory=time.time)
    timeout_seconds: int = 600
    expires_at: float | None = None
    risk_level: str = "medium"
    confirm_title: str = "确认执行操作"
    confirm_message: str = "请确认内容无误后再继续。"
    agent_task_id: int | None = None  # AgentTask 主键，用于确认/取消后回写监控状态
    message_id: int | None = None  # talk_message 主键，用于确认后回写结果


class HitlConfirmRequest(BaseModel):
    task_id: str = Field(..., description="暂停的任务标识")
    step_id: int = Field(..., description="待确认的步骤序号")
    confirmed: bool = Field(..., description="用户是否确认执行")
    modified_params: dict | None = Field(None, description="用户修改后的参数（如修改邮件正文）")
