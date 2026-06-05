from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.orm import relationship
from database import Base


class TalkSession(Base):
    __tablename__ = "talk_session"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    user_id = Column(String(100), nullable=False, index=True, comment="用户标识（对话隔离）")
    session_title = Column(String(200), default="新对话", comment="会话标题")
    summary = Column(Text, default=None, comment="对话主题摘要（大模型自动生成）")
    style = Column(String(100), default=None, comment="用户对话风格偏好（大模型自动识别）")
    is_deleted = Column(Integer, nullable=False, default=0, comment="逻辑删除 0-未删 1-已删")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    messages = relationship("TalkMessage", back_populates="session",
                            order_by="TalkMessage.create_time")


class TalkMessage(Base):
    __tablename__ = "talk_message"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id = Column(Integer, ForeignKey("talk_session.id"), nullable=False, index=True, comment="所属会话ID")
    role = Column(String(20), nullable=False, comment="角色: system / user / assistant")
    user_content = Column(Text, default=None, comment="用户问题（role=user 时有值）")
    ai_content = Column(Text, default=None, comment="大模型回复（role=assistant 时有值）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    session = relationship("TalkSession", back_populates="messages")
