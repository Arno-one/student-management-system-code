"""
教师管理业务逻辑层 — MVC中的Model业务逻辑部分
"""
from sqlalchemy.orm import Session
from typing import List, Literal, Optional
from datetime import datetime
from DAO.teacher_information_CRUD import teacher_table_CRUD
from model import Teacher
from scheme.teacher_scheme import POST_Teacher_Info, PUT_Teacher_Info, GET_Teacher_Info
import math


def get_teacher_by_id(id: int, db: Session) -> GET_Teacher_Info:
    """根据ID查询教师"""
    crud = teacher_table_CRUD(db)
    teacher = crud.read(id)
    if teacher is None:
        raise ValueError(f"教师ID {id} 不存在")
    return GET_Teacher_Info.model_validate(teacher)


def search_teachers(
    db: Session,
    name: str = None,
    gender: str = None,
    title: str = None,
    class_id: int = None,
    phone: str = None,
    email: str = None,
    hire_date_start: datetime = None,
    hire_date_end: datetime = None,
    sort_by: str = None,
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
):
    """分页搜索教师"""
    GENDER_TO_ENUM = {"男": Teacher.gender.man, "女": Teacher.gender.woman}
    crud = teacher_table_CRUD(db)

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

    items, total = crud.search(
        filters=filters, sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size,
    )

    return {
        "items": [GET_Teacher_Info.model_validate(t) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


def create_teachers(teacher_list: List[POST_Teacher_Info], db: Session):
    """批量创建教师"""
    crud = teacher_table_CRUD(db)
    new_teacher_orms = [Teacher.Teacher(**t.model_dump()) for t in teacher_list]
    crud.create(new_teacher_orms)


def update_teacher(id: int, data: PUT_Teacher_Info, db: Session):
    """更新教师信息"""
    crud = teacher_table_CRUD(db)
    update_dict = data.model_dump(exclude_none=True)
    crud.update(id, update_dict)


def delete_teacher(id: int, db: Session):
    """删除教师（逻辑删除）"""
    crud = teacher_table_CRUD(db)
    crud.delete(id)
