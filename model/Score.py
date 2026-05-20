from sqlalchemy import Column,String,Integer,DECIMAL,DateTime
from datetime import datetime
from database import Base,engine



#定义student_score表

class Score(Base):
    #定义mysql中的表名
    __tablename__ = "student_score"
    #定义字段
    id = Column(Integer,primary_key=True,autoincrement=True) #"成绩ID"
    student_no = Column(String(50),nullable=False) #学生编号
    exam_order = Column(Integer,nullable=False) #考核序次
    score = Column(DECIMAL(5,1),nullable=False) #学生成绩
    is_deleted = Column(Integer,default=0) #逻辑删除0-未删 1-已删
    create_time= Column(DateTime,default=datetime.now()) #创建时间
    update_time= Column(DateTime,default=datetime.now,onupdate=datetime.now) #更新时间


Base.metadata.create_all(engine)