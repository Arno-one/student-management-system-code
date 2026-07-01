"""Agent 用户反馈"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from database import Base


class AgentFeedback(Base):
    __tablename__ = "agent_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="反馈ID")
    task_id = Column(Integer, ForeignKey("agent_task.id"), nullable=False, index=True, comment="关联的任务ID")
    rating = Column(Integer, nullable=False, comment="评分 1-5")
    comment = Column(Text, nullable=True, comment="用户评语")
    tool_name = Column(String(50), nullable=True, comment="预留步骤级反馈: 针对哪个工具的评价")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
