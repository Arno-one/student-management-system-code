"""
学生管理业务逻辑层 — MVC中的Model业务逻辑部分
"""
from sqlalchemy.orm import Session
from typing import Optional
from DAO import student_dao
from scheme.student_scheme import StudentCreate, StudentUpdate


def create_student(data: StudentCreate, db: Session):
    """创建学生（含业务校验）"""
    # 业务校验：检查学号是否已存在
    existing = student_dao.get_by_student_no(data.student_no, db)
    if existing:
        raise ValueError(f"学号 {data.student_no} 已存在")

    create_data = {k: v for k, v in data.dict().items() if v is not None}
    return student_dao.create_from_dict(create_data, db)


def get_all_students(skip: int, limit: int, db: Session):
    """分页查询所有学生"""
    students = student_dao.get_all(skip, limit, db)
    total = student_dao.count(db)
    page = skip // limit + 1 if limit > 0 else 1
    return students, page, limit, total


def get_student_by_id(student_id: int, db: Session):
    """根据ID查询学生"""
    student = student_dao.get_by_id(student_id, db)
    if not student:
        raise ValueError(f"学生ID {student_id} 不存在")
    return student


def get_student_by_no(student_no: str, db: Session):
    """根据学号查询学生"""
    student = student_dao.get_by_student_no(student_no, db)
    if not student:
        raise ValueError(f"学号 {student_no} 不存在")
    return student


def get_students_by_class(class_id: int, skip: int, limit: int, db: Session):
    """根据班级查询学生"""
    result = student_dao.get_by_class(skip, limit, class_id, db)
    total = student_dao.get_by_class_count(class_id, db)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total


def update_student(student_id: int, data: StudentUpdate, db: Session):
    """更新学生信息"""
    update_dict = {k: v for k, v in data.dict().items() if v is not None}
    if not update_dict:
        raise ValueError("没有提供要更新的字段")

    student = student_dao.update(student_id, update_dict, db)
    if not student:
        raise ValueError(f"学生ID {student_id} 不存在")
    return student


def soft_delete_student(student_id: int, db: Session):
    """逻辑删除学生"""
    student = student_dao.get_by_id(student_id, db)
    if not student:
        raise ValueError(f"学生ID {student_id} 不存在或已删除")
    return student_dao.soft_delete(student_id, db)


def restore_student(student_id: int, db: Session):
    """恢复已删除学生"""
    success = student_dao.restore(student_id, db)
    if not success:
        raise ValueError(f"未找到已删除的学生ID {student_id}")
    return True
