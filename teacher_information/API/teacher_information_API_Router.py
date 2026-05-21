from fastapi import APIRouter, Depends
import database
from pydantic import BaseModel, EmailStr, field_validator
from DAO.teacher_information_CRUD import teacher_table_CRUD
from model import Teacher
from datetime import datetime

class POST_Teacher_Info(BaseModel):
    name: str
    gender: str
    birth_date: datetime | None = None
    phone: str
    email: EmailStr | None = None
    title: str
    class_id: int
    class_name:str
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

    @field_validator("gender", mode="before")
    @classmethod
    def convert_gender(cls, v):
        GENDER_MAP = {Teacher.gender.man: "男", Teacher.gender.woman: "女"}
        return GENDER_MAP.get(v, v)

teacher_information_router =APIRouter()

@teacher_information_router.get('/teachers/{id}')
def get_teacher(id:int,db=Depends(database.get_db))->GET_Teacher_Info:
    ti_CRUD_session=teacher_table_CRUD(db)
    temp_teachers_info=ti_CRUD_session.read(id)
    return GET_Teacher_Info.model_validate(temp_teachers_info)

@teacher_information_router.get('/teachers')
def get_teachers(db=Depends(database.get_db))->list[GET_Teacher_Info]:
    ti_CRUD_session=teacher_table_CRUD(db)
    temp_teachers_info=ti_CRUD_session.read()
    return [GET_Teacher_Info.model_validate(t) for t in temp_teachers_info]

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

