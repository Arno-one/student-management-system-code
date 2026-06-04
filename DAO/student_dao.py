from sqlalchemy.orm import Session
from model.Student import Student
from typing import Optional
from util.log import get_logger

# 本模块专用 logger，来源标记为 DAO.student_dao
logger = get_logger(__name__)

# ==================== 增（CREATE）====================
def create_from_dict(data: dict,db:Session) -> Student:

    """通过字典新增学生"""
    student = Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    # 写库成功（事务已提交），记录关键标识，便于追溯数据变更
    logger.info("学生已入库：id=%s, student_no=%s", student.id, student.student_no)
    return student

# ==================== 查（READ）====================
def get_all(skip: int, limit: int, db:Session):
    """分页查询所有学生"""
    return db.query(Student).filter(
        Student.is_deleted == 0
    ).offset(skip).limit(limit).all()

def count(db:Session):
    """统计未删除学生总数"""
    return db.query(Student).filter(Student.is_deleted == 0).count()

def get_by_id(student_id: int,db:Session) -> Optional[Student]:
    """根据学生ID查询"""
    return db.query(Student).filter(
        Student.id == student_id,
        Student.is_deleted == 0
    ).first()

def get_by_student_no(student_no: str,db:Session) -> Optional[Student]:
    """根据学号查询"""
    return db.query(Student).filter(
        Student.student_no == student_no,
        Student.is_deleted == 0
    ).first()

def get_by_class(skip: int, limit: int, class_id: int, db: Session):
    """根据班级ID查询"""
    result = (db.query(Student).filter(
        Student.class_id == class_id,
        Student.is_deleted == 0
    ).offset(skip).limit(limit).all())
    return result

def get_by_class_count(class_id: int, db: Session):
    result = (db.query(Student).filter(
        Student.class_id == class_id,
        Student.is_deleted == 0
    ).count())
    return result


# ==================== 改（UPDATE）====================
def update(student_id: int, update_data: dict, db:Session) -> Optional[Student]:
    """
            根据学生id更新学生信息（自动排除 id / student_no / create_time / is_deleted）
            """
    student = get_by_id(student_id,db)
    if not student:
        return None

    forbidden = {'id', 'student_no', 'create_time', 'is_deleted'}
    for key, value in update_data.items():
        if key not in forbidden and hasattr(student, key):
            setattr(student, key, value)

    db.commit()
    db.refresh(student)
    logger.info("学生信息已更新（事务已提交）：id=%s", student_id)
    return student

# ==================== 逻辑删除（DELETE）====================
def soft_delete(student_id: int, db:Session) -> bool:
    """
            逻辑删除单个学生
            返回 True/False 表示是否删除成功
            """
    student = get_by_id(student_id,db)
    if not student:
        return False

    student.is_deleted = 1
    db.commit()
    logger.info("学生已逻辑删除（事务已提交）：id=%s", student_id)
    return True


def restore(student_id: int,db:Session) -> bool:
    """恢复已逻辑删除的学生"""
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.is_deleted == 1
    ).first()
    if not student:
        return False

    student.is_deleted = 0
    db.commit()
    logger.info("学生已恢复（事务已提交）：id=%s", student_id)
    return True



