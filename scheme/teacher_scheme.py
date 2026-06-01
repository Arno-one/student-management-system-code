"""
教师模块的Pydantic请求/响应模型
从 API/teacher_information_API_Router.py 中提取，遵循 MVC 分离原则
"""
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from datetime import datetime
from typing import Optional, List
from model import Teacher


class POST_Teacher_Info(BaseModel):
    """创建教师请求模型"""
    name: str
    gender: str
    birth_date: datetime | None = None
    phone: str
    email: EmailStr | None = None
    title: str
    class_id: int
    hire_date: datetime

    @field_validator("gender", mode="before")
    @classmethod
    def convert_gender(cls, v):
        GENDER_MAP = {"男": Teacher.gender.man, "女": Teacher.gender.woman}
        return GENDER_MAP.get(v, v)


class PUT_Teacher_Info(BaseModel):
    """更新教师请求模型"""
    name: str | None = None
    gender: str | None = None
    birth_date: datetime | None = None
    phone: str | None = None
    email: EmailStr | None = None
    title: str | None = None
    class_id: int | None = None
    hire_date: datetime | None = None

    @field_validator("gender", mode="before")
    @classmethod
    def convert_gender(cls, v):
        if v is None:
            return v
        GENDER_MAP = {"男": Teacher.gender.man, "女": Teacher.gender.woman}
        return GENDER_MAP.get(v, v)


class GET_Teacher_Info(BaseModel):
    """教师查询响应模型"""
    model_config = {"from_attributes": True}
    id: int
    name: str
    gender: str
    birth_date: datetime | None = None
    phone: str
    email: EmailStr | None = None
    title: str
    class_id: int
    hire_date: datetime
    class_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_class_name(cls, data):
        if hasattr(data, "classname") and data.classname:
            data.class_name = data.classname.class_name
        return data

    @field_validator("gender", mode="before")
    @classmethod
    def convert_gender(cls, v):
        GENDER_MAP = {Teacher.gender.man: "男", Teacher.gender.woman: "女"}
        return GENDER_MAP.get(v, v)


class PagedTeacherResponse(BaseModel):
    """教师分页查询响应模型"""
    items: List[GET_Teacher_Info]
    total: int
    page: int
    page_size: int
    total_pages: int