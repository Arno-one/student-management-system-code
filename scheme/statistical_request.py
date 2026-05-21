from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, TypeVar, Generic
from datetime import date, datetime


# 年龄大于30的学生响应
class StudentGe30Response(BaseModel):
    id: int = Field(..., description="学生ID")
    student_no: str
    student_name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    native_place: Optional[str] = None
    graduate_school: Optional[str] = None
    major: Optional[str] = None
    education: Optional[str] = None
    admission_time: Optional[date] = None
    graduate_time: Optional[date] = None

    class Config:
        from_attributes = True


# 学生统计响应
class StudentCountResponse(BaseModel):
    全体人数: int
    男生人数: int
    女生人数: int


# 每次考试都在80分以上的学生响应
class ScoreGe80Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_no: str
    student_name: str
    score: float


# 2次以上不及格的学生响应
class ScoreLe60Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_no: str
    student_name: str
    score: float


# 班级平均分响应
class ClassAvgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    class_name: str
    exam_order: int
    avg_score: float


# 薪资最高的5个人响应
class TallSalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_name: str
    company_name: str
    offer_send_time: Optional[date] = None
    salary: int
    class_name: str


# 学生就业时长响应
class JobTimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_name: str
    job_duration_days: int


# 班级平均就业时长响应
class AvgClassJobTimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    class_name: str
    avg_days: float


# 通用分页响应
T = TypeVar('T')

class PageResponse(BaseModel, Generic[T]):
    code: int = 200
    data: List[T]
    page: int
    total: int
