"""
统计分析业务逻辑层 — MVC中的Model业务逻辑部分

统计分析模块的DAO已包含复杂查询逻辑，
Service主要作为统一的调用入口和参数验证。
"""
from sqlalchemy.orm import Session
from DAO import statistical as dao


def get_student_by_age(skip: int, limit: int, age: int, db: Session):
    """查询年龄大于指定值的学生"""
    result = dao.get_student_age(db, skip, age, limit)
    total = dao.get_student_age_count(db, age)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total


def get_student_count(db: Session):
    """统计学生人数"""
    return dao.get_student_count(db)


def get_scores_above(skip: int, limit: int, grade: int, db: Session):
    """查询每次考试都在指定分数以上的学生"""
    result = dao.get_score_grade(db, skip, grade, limit)
    total = dao.get_score_grade_count(db, grade)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total


def get_score_fails(skip: int, limit: int, db: Session):
    """查询2次以上不及格的学生"""
    result = dao.get_score_fails(db, skip, limit)
    total = dao.get_score_fails_count(db)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total


def get_class_average(skip: int, limit: int, db: Session):
    """查询每个班级每次考试的平均分"""
    result = dao.get_class_avg(db, skip, limit)
    total = dao.get_class_avg_count(db)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total


def get_top_salaries(limit: int, db: Session):
    """查询薪资最高的前N人"""
    result = dao.get_tall_sal(db, limit)
    return result, 1, limit, len(result)


def get_job_durations(skip: int, limit: int, db: Session):
    """查询每个学生的就业时长"""
    result = dao.get_job_time(db, skip, limit)
    total = dao.get_job_time_count(db)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total


def get_avg_class_job_time(skip: int, limit: int, db: Session):
    """查询每个班级的平均就业时长"""
    result = dao.avg_class_job_time(db, skip, limit)
    total = dao.get_avg_class_job_time_count(db)
    page = skip // limit + 1 if limit > 0 else 1
    return result, page, limit, total
