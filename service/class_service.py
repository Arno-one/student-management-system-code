"""
班级管理业务逻辑层 — MVC中的Model业务逻辑部分
"""
from sqlalchemy.orm import Session
from DAO import class_dao
from scheme.class_scheme import ClassCreateSchema


def create_or_update_class(data: ClassCreateSchema, db: Session, id: int = None):
    """新增或修改班级（含业务校验）"""
    result = class_dao.create_or_update_class(db=db, class_data=data, id=id)
    if not result:
        raise ValueError("新增数据班级编号不能重复")
    return result


def delete_class(id: int, db: Session):
    """删除班级"""
    return class_dao.del_class(db=db, id=id)


def get_classes(page: int, limit: int, db: Session):
    """分页查询班级"""
    info = class_dao.get_class(db=db, page=page - 1, limit=limit)
    return info, page, limit, len(info)


def get_class_by_id(id: int, db: Session):
    """根据ID查询班级"""
    result = class_dao.get_class_by_id(db=db, id=id)
    if isinstance(result, str):
        raise ValueError(result)
    return result
