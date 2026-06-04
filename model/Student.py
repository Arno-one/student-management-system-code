from sqlalchemy import Column,Integer,String,Date,DateTime
from datetime import datetime
from sqlalchemy.orm import relationship
from database import Base,engine

# 定义学生类，继承Base基类，这个类对应数据库中的一张表
class Student(Base):
    # 定义mysql中实际的表名
    __tablename__ = "student"
    # 定义字段
    id =  Column(Integer,primary_key=True,index=True,autoincrement=True,comment='学生id')
    student_no = Column(String(50),unique=True,nullable=False,index=True,comment='学生学号')
    class_id = Column(Integer,nullable=False,index=True,comment='班级ID')
    student_name = Column(String(50),nullable=False,index=True,comment='学生姓名')
    gender = Column(String(10),default=None,comment='性别')
    age = Column(Integer,default=None,index=True,comment='年龄')
    native_place = Column(String(100),default=None,comment='籍贯')
    graduate_school = Column(String(100),default=None,comment='毕业院校')
    major = Column(String(100),default=None,comment='专业')
    education = Column(String(50),default=None,comment='学历')
    admission_time = Column(Date,default=None,comment="入学时间")
    graduate_time = Column(Date,default=None,comment="毕业时间")
    advisor_id = Column(Integer,default=None,comment='顾问编号')
    is_deleted = Column(Integer,nullable=False,default="0",comment='逻辑删除 0-未删 1-已删')
    create_time = Column(DateTime,default=datetime.now,comment="创建时间")
    update_time = Column(DateTime,default=datetime.now,onupdate=datetime.now,comment="更新时间")
    score_list = relationship("Score", back_populates="student")