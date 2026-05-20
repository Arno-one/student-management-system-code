from sqlalchemy import Column, Integer, String, DateTime,Date,func
from database import Base
class Employment(Base):
    __tablename__ = 'employment'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="就业ID")
    student_no = Column(String(50), unique=True, comment="学生编号")
    student_name = Column(String(50), comment="学生姓名（冗余）")
    class_id = Column(Integer, comment="班级ID（冗余）")
    job_open_time = Column(Date, comment="就业开放时间")
    offer_send_time = Column(Date, comment="offer下发时间")
    company_name = Column(String(100), comment="就业公司")
    salary = Column(Integer, comment="就业薪资")
    is_deleted = Column(Integer, default=0, comment="逻辑删除 0-未删 1-已删")
    create_time = Column(DateTime,comment="创建时间")
    update_time = Column(DateTime,comment="更新时间")
