from database import Base, engine
from sqlalchemy import Column, Integer, String,DateTime
from datetime import datetime

class Class(Base):
    __tablename__ = 'class_info'
    id = Column(Integer,primary_key=True,autoincrement=True,comment="班级ID")
    class_code = Column(String(50),unique=True,nullable=False,comment="班级编号")
    class_name = Column(String(50),nullable=False,comment="班级名称")
    start_time = Column(DateTime,nullable=False,comment="开班时间")
    is_deleted = Column(Integer,default=0,comment="逻辑删除 0-未删 1-已删")
    create_time = Column(DateTime,default=datetime.now,comment="创建时间")
    update_time = Column(DateTime,default=datetime.now,comment="更新时间")