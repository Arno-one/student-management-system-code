"""
班级数据访问层 — 负责班级相关的数据库操作
"""
from model.Class import Class
from datetime import datetime
from util.log import get_logger

# 本模块专用 logger，来源标记为 DAO.class_dao
logger = get_logger(__name__)


def create_or_update_class(db, class_data, id=None):
    """新增或修改班级数据"""
    if id is not None:
        class_to_update = db.query(Class).filter(Class.id == id).first()
        if not class_to_update:
            logger.warning("修改班级失败：id=%s 不存在", id)
            return None
        for key, value in class_data.model_dump().items():
            setattr(class_to_update, key, value)
        db_obj = class_to_update
        db_obj.update_time = datetime.now()
    else:
        if get_class_by_code(db, class_data.class_code):
            logger.warning("新增班级失败：班级编号 %s 已存在", class_data.class_code)
            return None
        db_obj = Class(**class_data.model_dump())

    try:
        db.commit()
        db.refresh(db_obj)
        logger.info("班级%s成功（事务已提交）：id=%s", "修改" if id else "新增", db_obj.id)
        return db_obj
    except Exception as e:
        # 关键修复：原先异常被直接吞掉，排查无门。这里回滚并记完整堆栈进 error.log
        db.rollback()
        logger.exception("班级新增/修改异常，已回滚事务：id=%s, %s", id, e)
        return None


def del_class(db, id):
    """逻辑删除班级"""
    try:
        class_to_del = db.query(Class).filter(
            Class.id == id,
            Class.is_deleted == 0
        ).first()
        if not class_to_del:
            logger.warning("删除班级失败：id=%s 不存在或已删除", id)
            return None
        class_to_del.is_deleted = 1
        db.commit()
        db.refresh(class_to_del)
        logger.info("班级已逻辑删除（事务已提交）：id=%s", id)
        return class_to_del
    except Exception as e:
        # 同样：补上回滚 + 异常日志，避免删除失败时悄无声息
        db.rollback()
        logger.exception("删除班级异常，已回滚事务：id=%s, %s", id, e)
        return None


def get_class(db, page, limit):
    """分页查询所有班级"""
    return db.query(Class).filter(
        Class.is_deleted == 0
    ).offset(page * limit).limit(limit).all()


def get_class_by_id(db, id):
    """根据ID查询班级"""
    return db.query(Class).filter(
        Class.id == id,
        Class.is_deleted == 0
    ).first()


def get_class_by_code(db, code):
    """根据班级编号查询（返回True表示编号可用，False表示已存在）"""
    class_by_code = db.query(Class).filter(
        Class.class_code == code,
        Class.is_deleted == 0
    ).first()
    return False if class_by_code else True
