from fastapi import APIRouter, Depends
import database
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from DAO.teacher_information_CRUD import teacher_table_CRUD
from model import Teacher
from datetime import datetime
from typing import Literal
import math

class POST_Teacher_Info(BaseModel):
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

class PUT_Teacher_Info(POST_Teacher_Info):
    name: str | None = None
    gender: str | None = None
    phone: str | None = None
    title: str | None = None
    class_id: int | None = None
    hire_date: datetime | None = None

class GET_Teacher_Info(POST_Teacher_Info):
    model_config = {"from_attributes": True}
    id: int
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
    items: list[GET_Teacher_Info]
    total: int
    page: int
    page_size: int
    total_pages: int

teacher_information_router =APIRouter()

@teacher_information_router.get('/teachers/{id}')
def get_teacher(id:int,db=Depends(database.get_db))->GET_Teacher_Info:
    ti_CRUD_session=teacher_table_CRUD(db)
    temp_teachers_info=ti_CRUD_session.read(id)
    return GET_Teacher_Info.model_validate(temp_teachers_info)

@teacher_information_router.get('/teachers')
def get_teachers(
    name: str | None = None,
    gender: Literal["男", "女"] | None = None,
    title: str | None = None,
    class_id: int | None = None,
    phone: str | None = None,
    email: str | None = None,
    hire_date_start: datetime | None = None,
    hire_date_end: datetime | None = None,
    sort_by: Literal["id", "name", "hire_date", "create_time", "class_id"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    page: int = 1,
    page_size: int = 20,
    db=Depends(database.get_db),
) -> PagedTeacherResponse:
    GENDER_TO_ENUM = {"男": Teacher.gender.man, "女": Teacher.gender.woman}
    ti_CRUD_session = teacher_table_CRUD(db)

    filters = {
        "name": name,
        "title": title,
        "class_id": class_id,
        "phone": phone,
        "email": email,
        "hire_date_start": hire_date_start,
        "hire_date_end": hire_date_end,
    }
    if gender:
        filters["gender"] = GENDER_TO_ENUM.get(gender)

    items, total = ti_CRUD_session.search(
        filters=filters, sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size,
    )
    return PagedTeacherResponse(
        items=[GET_Teacher_Info.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )

@teacher_information_router.post('/teachers')
def post_teachers(temp_new_teachers:list[POST_Teacher_Info],db=Depends(database.get_db)):
    ti_CRUD_session=teacher_table_CRUD(db)
    new_teacher_orms = [Teacher.Teacher(**t.model_dump()) for t in temp_new_teachers]
    ti_CRUD_session.create(new_teacher_orms)
    return {'message':'创建成功'}

@teacher_information_router.put('/teachers/{id}')
def put_teacher(id:int,temp_teacher_update_info:PUT_Teacher_Info,db=Depends(database.get_db)):
    ti_CRUD_session=teacher_table_CRUD(db)
    temp_dict = temp_teacher_update_info.model_dump(exclude_none=True)
    ti_CRUD_session.update(id,temp_dict)
    return {'message':'更新成功'}

