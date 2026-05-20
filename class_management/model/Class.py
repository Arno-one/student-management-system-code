from database import Base, engine
from sqlalchemy import Column, Integer, String,DateTime
from datetime import datetime


class class_management(Base):
    __tablename__ = 'class_info'
    id = Column(Integer,primary_key=True,autoincrement=True)
    class_code = Column(String(50),nullable=False)
    name = Column(String(50),nullable=False)
    start_time = Column(DateTime,nullable=False)
    head_teacher_id = Column(Integer,nullable=False)
    lecturer_id = Column(Integer,nullable=False)
    created_time = Column(DateTime,default=datetime.now)
    updated_time = Column(DateTime,default=datetime.now)
    deleted_at = Column(Integer,default=0)

Base.metadata.create_all(engine)