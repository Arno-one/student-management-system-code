"""
就业管理业务逻辑层 — MVC中的Model业务逻辑部分
"""
from sqlalchemy.orm import Session
from DAO import employment_dao as dao
from scheme.employment_scheme import EmploymentCreate, EmploymentUpdate


def create_employment(data: EmploymentCreate, db: Session):
    """创建就业信息（含业务校验）"""
    emp = dao.get_employment_by_student_no(db, data.student_no)
    if emp:
        raise ValueError("就业信息已存在")
    return dao.create_employment(db, data)


def get_employment_by_id(emp_id: int, db: Session):
    """根据ID查询就业信息"""
    emp = dao.get_employment_by_id(db, emp_id)
    if not emp:
        raise ValueError("就业信息不存在")
    return emp


def get_employment_list(
    db: Session,
    page: int = 1,
    size: int = 10,
    student_name: str = None,
    class_id: int = None,
    company_name: str = None,
):
    """分页查询就业信息"""
    return dao.get_employment_list(db, page, size, student_name, class_id, company_name)


def update_employment(emp_id: int, data: EmploymentUpdate, db: Session):
    """更新就业信息（含业务校验）"""
    emp = dao.get_employment_by_id(db, emp_id)
    if not emp:
        raise ValueError("就业信息不存在")

    # 校验学生编号是否被占用
    if data.student_no:
        duplicate = dao.check_student_no(db, emp_id, data)
        if duplicate:
            raise ValueError("学生编号已存在")

    return dao.update_employment(db, emp, data)


def soft_delete_employment(emp_id: int, db: Session):
    """逻辑删除就业信息"""
    emp = dao.get_employment_by_id(db, emp_id)
    if not emp:
        raise ValueError("就业信息不存在")
    return dao.delete_employment(db, emp)


def recover_employment(emp_id: int, db: Session):
    """恢复就业信息"""
    emp = dao.get_employment_id_all(db, emp_id)
    if not emp:
        raise ValueError("就业信息不存在")
    if emp.is_deleted == 0:
        raise ValueError("数据无需恢复")
    return dao.recover_employment(db, emp)


def hard_delete_employment(emp_id: int, db: Session):
    """物理删除就业信息"""
    emp = dao.get_employment_id_all(db, emp_id)
    if not emp:
        raise ValueError("就业信息不存在")
    return dao.hard_delete_employment(db, emp)
