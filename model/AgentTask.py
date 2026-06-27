"""Agent 任务执行记录"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from database import Base


class AgentTask(Base):
    __tablename__ = "agent_task"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="任务ID")
    session_id = Column(Integer, ForeignKey("talk_session.id"), nullable=True, index=True, comment="关联的 Agent 会话ID")
    user_id = Column(String(100), nullable=False, index=True, comment="用户标识")
    persona = Column(String(50), default="academic_mentor", comment="使用的角色标识")
    intent = Column(String(50), comment="识别到的意图")
    original_message = Column(Text, comment="用户原始输入")
    rewritten_message = Column(Text, nullable=True, comment="中间件改写后的消息（如有）")
    plan_json = Column(Text, nullable=True, comment="生成的执行计划 JSON")
    steps_json = Column(Text, nullable=True, comment="各步骤执行结果 JSON")
    status = Column(String(30), default="pending", comment="状态: pending/running/awaiting_hitl/success/error/cancelled")
    total_duration_ms = Column(Integer, default=0, comment="总耗时（毫秒）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
