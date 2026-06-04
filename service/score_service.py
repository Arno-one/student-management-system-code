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
from util.log import get_logger

# 本模块专用 logger，来源标记为 service.score_service
logger = get_logger(__name__)


def add_score(data: Addscore, db: Session):
    """添加单个学生成绩（含业务校验）"""
    # 业务校验：学生是否存在
    exist = get_by_student_no(data.student_no, db)
    if not exist:
        logger.warning("新增成绩校验失败：学生 %s 不在学生表中", data.student_no)
        raise ValueError(f"学生 {data.student_no} 的信息不在学生表中")

    # 业务校验：成绩是否已存在
    is_exist = score_dao.is_exist(db, data.student_no, data.exam_order)
    if is_exist:
        logger.warning("新增成绩校验失败：学生 %s 第%s次成绩已存在",
                       data.student_no, data.exam_order)
        raise ValueError(f"学生 {data.student_no} 的第{data.exam_order}次成绩已经存在")

    new_score = Score(
        student_no=data.student_no,
        exam_order=data.exam_order,
        score=data.score
    )
    return score_dao.add_score(db, new_score)


def batch_add_scores(score_list: List[Addscore], db: Session):
    """批量添加学生成绩（含业务校验）"""
    # 批量操作是关键节点，先记一条入口日志，标明本批次条数
    logger.info("批量新增成绩开始：本批次 %s 条", len(score_list))
    # 业务校验：检查所有学生是否存在
    not_exist = []
    for item in score_list:
        exist = get_by_student_no(item.student_no, db)
        if not exist:
            not_exist.append(item.student_no)
    if not_exist:
        logger.warning("批量新增成绩校验失败：以下学生不在学生表中 %s", not_exist)
        raise ValueError(f"学生 {not_exist} 的信息不在学生表中")

    # 业务校验：检查是否有重复数据
    batch_data = []
    for item in score_list:
        is_exist = score_dao.is_exist(db=db, student_no=item.student_no, exam_order=item.exam_order)
        if is_exist:
            logger.warning("批量新增成绩校验失败：学生 %s 第%s次成绩已存在",
                           item.student_no, item.exam_order)
            raise ValueError(f"学生 {item.student_no} 第{item.exam_order}次成绩已存在")

        batch_data.append(Score(
            student_no=item.student_no,
            exam_order=item.exam_order,
            score=item.score
        ))

    result = score_dao.batch_add_scores(db, batch_data)
    logger.info("批量新增成绩完成：成功入库 %s 条", len(result))
    return result


def update_score(data: Updatescore, db: Session):
    """更新学生成绩（含业务校验）"""
    is_exist = score_dao.is_exist(db, data.student_no, data.exam_order)
    if not is_exist:
        logger.warning("修改成绩校验失败：学生 %s 第%s次成绩不存在",
                       data.student_no, data.exam_order)
        raise ValueError("要修改的学生信息不存在")
    return score_dao.update_score(db, data.student_no, data.exam_order, data.score)


def soft_delete_score(student_no: str, exam_order: int, db: Session):
    """逻辑删除学生成绩（含业务校验）"""
    is_exist = score_dao.is_exist(db, student_no, exam_order)
    if not is_exist:
        logger.warning("删除成绩校验失败：学生 %s 第%s次成绩不存在", student_no, exam_order)
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
            logger.warning("查询成绩校验失败：最小范围 %s 大于最大范围 %s", min_score, max_score)
            raise ValueError("请求异常,最小范围不能大于最大范围")

    result = score_dao.query_score(
        db, page, page_size,
        student_no, exam_order, class_id,
        min_score, max_score,
        sort_no, sort_score
    )

    if not result:
        logger.warning("查询成绩：无符合条件的数据，student_no=%s, exam_order=%s, class_id=%s",
                       student_no, exam_order, class_id)
        raise ValueError("要查询的学生信息不存在")

    # 用独立的计数方法拿到满足条件的总条数，供分页返回 total
    total = score_dao.count_score(
        db, student_no, exam_order, class_id, min_score, max_score
    )

    return result, page, page_size, total
