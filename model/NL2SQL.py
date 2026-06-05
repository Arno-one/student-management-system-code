from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from datetime import datetime
from sqlalchemy.orm import relationship
from database import Base


class Nl2sqlSession(Base):
    __tablename__ = "nl2sql_session"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    user_id = Column(String(100), nullable=False, index=True, comment="用户标识（对话隔离）")
    title = Column(String(200), default="新对话", comment="会话标题")
    is_deleted = Column(Integer, nullable=False, default=0, comment="逻辑删除 0-未删 1-已删")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    messages = relationship("Nl2sqlMessage", back_populates="session",
                            order_by="Nl2sqlMessage.create_time")


class Nl2sqlMessage(Base):
    __tablename__ = "nl2sql_message"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id = Column(Integer, ForeignKey("nl2sql_session.id"), nullable=False, index=True, comment="所属会话ID")
    question = Column(Text, nullable=False, comment="用户自然语言问题")
    generated_sql = Column(Text, default=None, comment="大模型生成的SQL语句")
    result_json = Column(Text, default=None, comment="查询结果JSON")
    cost_ms = Column(Integer, default=None, comment="LLM调用耗时（毫秒）")
    is_cached = Column(Integer, default=0, comment="是否命中缓存 0-否 1-是")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    session = relationship("Nl2sqlSession", back_populates="messages")
