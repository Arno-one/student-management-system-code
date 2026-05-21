from database import Base,engine
import enum
from datetime import datetime
from sqlalchemy import Column,Integer,String,Enum,DateTime
from sqlalchemy.orm import relationship

class gender(enum.Enum):
    man=1
    woman=2

class Teacher(Base):
    __tablename__='Teacher'
    id=Column(Integer,primary_key=True,index=True,autoincrement=True,comment="主键")
    name=Column(String(50),nullable=False,index=True,comment="教师姓名")
    gender=Column(Enum(gender),comment='性别')
    birth_date=Column(DateTime,comment="出生日期")
    phone=Column(String(20),nullable=False,comment='联系电话')
    email=Column(String(100),comment='邮箱')
    title=Column(String(50),nullable=False,comment='职务')
    class_id=Column(Integer,comment='所带班级')
    classname=relationship("Class",primaryjoin="foreign(Teacher.class_id)==Class.id")
    hire_date=Column(DateTime,nullable=False,comment='入职日期')
    create_time=Column(DateTime,default=datetime.now,comment='创建时间')
    update_time=Column(DateTime,onupdate=datetime.now,comment='更新时间')
    is_deleted=Column(Integer,default=0,comment='逻辑删除:0未删除，1已删除')


if __name__=="__main__":
    Base.metadata.create_all(engine)