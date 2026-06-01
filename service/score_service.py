"""
成绩管理业务逻辑层 — MVC中的Model业务逻辑部分
"""
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List, Optional
from DAO import score_dao
from DAO.student_dao import get_by_student_no
from model.Score import Score
from scheme.schema_score import Addscore, Updatescore


def add_score(data: Addscore, db: Session):
    """添加单个学生成绩（含业务校验）"""
    # 业务校验：学生是否存在
    exist = get_by_student_no(data.student_no, db)
    if not exist:
        raise ValueError(f"学生 {data.student_no} 的信息不在学生表中")

    # 业务校验：成绩是否已存在
    is_exist = score_dao.is_exist(db, data.student_no, data.exam_order)
    if is_exist:
        raise ValueError(f"学生 {data.student_no} 的第{data.exam_order}次成绩已经存在")

    new_score = Score(
        student_no=data.student_no,
        exam_order=data.exam_order,
        score=data.score
    )
    return score_dao.add_score(db, new_score)


def batch_add_scores(score_list: List[Addscore], db: Session):
    """批量添加学生成绩（含业务校验）"""
    # 业务校验：检查所有学生是否存在
    not_exist = []
    for item in score_list:
        exist = get_by_student_no(item.student_no, db)
        if not exist:
            not_exist.append(item.student_no)
    if not_exist:
        raise ValueError(f"学生 {not_exist} 的信息不在学生表中")

    # 业务校验：检查是否有重复数据
    batch_data = []
    for item in score_list:
        is_exist = score_dao.is_exist(db=db, student_no=item.student_no, exam_order=item.exam_order)
        if is_exist:
            raise ValueError(f"学生 {item.student_no} 第{item.exam_order}次成绩已存在")

        batch_data.append(Score(
            student_no=item.student_no,
            exam_order=item.exam_order,
            score=item.score
        ))

    return score_dao.batch_add_scores(db, batch_data)


def update_score(data: Updatescore, db: Session):
    """更新学生成绩（含业务校验）"""
    is_exist = score_dao.is_exist(db, data.student_no, data.exam_order)
    if not is_exist:
        raise ValueError("要修改的学生信息不存在")
    return score_dao.update_score(db, data.student_no, data.exam_order, data.score)


def soft_delete_score(student_no: str, exam_order: int, db: Session):
    """逻辑删除学生成绩（含业务校验）"""
    is_exist = score_dao.is_exist(db, student_no, exam_order)
    if not is_exist:
        raise ValueError("要删除的学生信息不存在")
    return score_dao.is_delete(db, student_no, exam_order)


def query_scores(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    student_no: str = None,
    exam_order: int = None,
    class_id: int = None,
    min_score: Decimal = None,
    max_score: Decimal = None,
    sort_no: str = None,
    sort_score: str = None,
):
    """查询学生成绩（含业务校验）"""
    # 业务校验：成绩范围合法性
    if min_score is not None and max_score is not None:
        if min_score > max_score:
            raise ValueError("请求异常,最小范围不能大于最大范围")

    result = score_dao.query_score(
        db, page, page_size,
        student_no, exam_order, class_id,
        min_score, max_score,
        sort_no, sort_score
    )

    if not result:
        raise ValueError("要查询的学生信息不存在")

    return result, page, page_size
