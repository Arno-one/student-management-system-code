from database import Base, engine
from sqlalchemy import Column, Integer, String,DateTime
from pydantic import BaseModel
from datetime import datetime

class ClassCreateSchema(BaseModel):
    class_code: str
    class_name: str
    start_time: datetime
    head_teacher_id: int
    lecturer_id: int


class Class(Base):
    __tablename__ = 'class_info'
    id = Column(Integer,primary_key=True,autoincrement=True,comment="班级ID")
    class_code = Column(String(50),nullable=False,comment="班级编号")
    class_name = Column(String(50),nullable=False,comment="班级名称")
    start_time = Column(DateTime,nullable=False,comment="开班时间")
    head_teacher_id = Column(Integer,nullable=False,comment="班主任ID")
    lecturer_id = Column(Integer,nullable=False,comment="授课老师ID")
    is_deleted = Column(Integer,default=0,comment="逻辑删除 0-未删 1-已删")
    created_time = Column(DateTime,default=datetime.now,comment="创建时间")
    updated_time = Column(DateTime,default=datetime.now,comment="更新时间")

Base.metadata.create_all(engine)