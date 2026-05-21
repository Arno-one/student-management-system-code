from sqlalchemy.orm import Session
from student_information.model.student import Student
from typing import Optional

# ==================== 增（CREATE）====================
def create_from_dict(data: dict,db:Session) -> Student:

    """通过字典新增学生"""
    student = Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

# ==================== 查（READ）====================
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

def get_by_class(page: int, limit: int, class_id: int, db: Session):
    """根据班级ID查询"""
    result = (db.query(Student).filter(
        Student.class_id == class_id,
        Student.is_deleted == 0
    ).offset(page).limit(limit).all())
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
    return True

