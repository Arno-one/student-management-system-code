# 不操作数据库，只负责校验数据格式
# 规定前端传什么数据给后端，后端返回什么数据给前端
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

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


class StudentExtract(BaseModel):
    """LLM 自然语言提取学生信息 — 所有字段 Optional，LLM 不编造缺失信息"""
    student_no: Optional[str] = Field(None, description="学号，如 S2024001")
    class_id: Optional[int] = Field(None, description="班级ID")
    student_name: Optional[str] = Field(None, description="姓名")
    gender: Optional[str] = Field(None, description="性别")
    age: Optional[int] = Field(None, description="年龄")
    native_place: Optional[str] = Field(None, description="籍贯")
    graduate_school: Optional[str] = Field(None, description="毕业院校")
    major: Optional[str] = Field(None, description="专业")
    education: Optional[str] = Field(None, description="学历")
    admission_time: Optional[date] = Field(None, description="入学时间")
    graduate_time: Optional[date] = Field(None, description="毕业时间")
    advisor_id: Optional[int] = Field(None, description="顾问编号")


class StudentUpdateExtract(BaseModel):
    """LLM 自然语言提取学生修改意图 — 区分定位条件和变更字段"""
    student_id: Optional[int] = Field(None, description="学生ID")
    student_no: Optional[str] = Field(None, description="学号")
    student_name: Optional[str] = Field(None, description="当前姓名（辅助定位）")
    changes: Optional["StudentChangeFields"] = Field(None, description="要修改的字段")


class StudentChangeFields(BaseModel):
    """可变更的学生字段"""
    class_id: Optional[int] = Field(None, description="班级ID")
    student_name: Optional[str] = Field(None, description="新姓名")
    gender: Optional[str] = Field(None, description="性别")
    age: Optional[int] = Field(None, description="年龄")
    native_place: Optional[str] = Field(None, description="籍贯")
    graduate_school: Optional[str] = Field(None, description="毕业院校")
    major: Optional[str] = Field(None, description="专业")
    education: Optional[str] = Field(None, description="学历")
    admission_time: Optional[date] = Field(None, description="入学时间")
    graduate_time: Optional[date] = Field(None, description="毕业时间")
    advisor_id: Optional[int] = Field(None, description="顾问编号")


