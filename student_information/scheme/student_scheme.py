# 不操作数据库，只负责校验数据格式
# 规定前端传什么数据给后端，后端返回什么数据给前端
from fastapi import Query
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import Optional, Any
from datetime import date, datetime

class StudentCreate(BaseModel):
    """创建学生请求模型"""
    student_no: str = Field(..., description="学生学号", json_schema_extra={"example": "S2024001"})
    class_id: int = Field(..., description="班级ID", json_schema_extra={"example": 1})
    student_name: str = Field(..., description="学生姓名", json_schema_extra={"example": "张三"})
    gender: Optional[str] = Field(None, description="性别", json_schema_extra={"example": "男"})
    age: Optional[int] = Field(0, description="年龄", json_schema_extra={"example": 20})
    native_place: Optional[str] = Field(None, description="籍贯", json_schema_extra={"example": "北京市"})
    graduate_school: Optional[str] = Field(None, description="毕业院校", json_schema_extra={"example": "北京一中"})
    major: Optional[str] = Field(None, description="专业", json_schema_extra={"example": "计算机科学"})
    education: Optional[str] = Field(None, description="学历", json_schema_extra={"example": "本科"})
    admission_time: Optional[date] = Field(None, description="入学时间")
    graduate_time: Optional[date] = Field(None, description="毕业时间")
    advisor_id: Optional[int] = Field(0, description="顾问编号", json_schema_extra={"example": 1})

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_no": "S2024001",
                "class_id": 1,
                "student_name": "张三",
                "gender": "男",
                "age": 20,
                "major": "计算机科学"
            }
        }
    }

class StudentUpdate(BaseModel):
    """更新学生请求模型"""
    class_id: Optional[int] = Field(None, description="班级ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    gender: Optional[str] = Field(None, description="性别")
    age: Optional[int] = Field(None, description="年龄")
    native_place: Optional[str] = Field(None, description="籍贯")
    graduate_school: Optional[str] = Field(None, description="毕业院校")
    major: Optional[str] = Field(None, description="专业")
    education: Optional[str] = Field(None, description="学历")
    admission_time: Optional[date] = Field(None, description="入学时间")
    graduate_time: Optional[date] = Field(None, description="毕业时间")
    advisor_id: Optional[int] = Field(None, description="顾问编号")

class StudentResponse(BaseModel):
    """学生响应模型"""
    id: int
    student_no: str
    class_id: int
    student_name: str
    gender: Optional[str]
    age: Optional[int]
    native_place: Optional[str]
    graduate_school: Optional[str]
    major: Optional[str]
    education: Optional[str]
    admission_time: Optional[date]
    graduate_time: Optional[date]
    advisor_id: Optional[int]
    is_deleted: int
    create_time: datetime
    update_time: datetime

    # 允许 Pydantic 模型读取 SQLAlchemy 数据库对象
    model_config = ConfigDict(from_attributes=True)

class ApiResponse(BaseModel):
    """统一响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
    total: Optional[int] = None
    page: int = 1
    limit : int = 10

    # 配置：允许装任意类型的数据（比如SQLAlchemy模型对象）
    model_config = ConfigDict(arbitrary_types_allowed=True)