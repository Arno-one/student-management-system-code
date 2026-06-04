"""
统计分析Controller层 — MVC中的Controller
只负责HTTP请求/响应处理，不包含业务逻辑
"""
from fastapi import APIRouter, Depends, Query
from database import get_db
from scheme.response_scheme import success_page, success
from service import statistical_service
from util.log import get_logger

# 本模块专用 logger，来源标记为 API.statistical
logger = get_logger(__name__)

sta_router = APIRouter()


@sta_router.get('/ge_stu/plus', summary='查询年龄大于xx的学生')
def get_student_age(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, default=10),
    age: int = Query(default=30, min=0),
    db=Depends(get_db)
):
    logger.info("统计-查询年龄大于%s的学生：skip=%s, limit=%s", age, skip, limit)
    result, page, page_size, total = statistical_service.get_student_by_age(
        skip, limit, age, db
    )
    return success_page(result, page, page_size, total)


@sta_router.get('/stu_count', summary='统计学生人数')
def get_student_count(db=Depends(get_db)):
    logger.info("统计-学生总人数")
    result = statistical_service.get_student_count(db)
    return success(result)


@sta_router.get('/score_greater/plus',
                summary='查询每次考试都在xx分以上的学生信息')
def get_score_grade(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, default=10),
    grade: int = Query(default=80, min=0),
    db=Depends(get_db)
):
    logger.info("统计-每次考试都在%s分以上的学生：skip=%s, limit=%s", grade, skip, limit)
    result, page, page_size, total = statistical_service.get_scores_above(
        skip, limit, grade, db
    )
    return success_page(result, page, page_size, total)


@sta_router.get('/score_fails',
                summary='查询2次以上不及格学生的信息')
def get_score_fails(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, default=10),
    db=Depends(get_db)
):
    logger.info("统计-2次以上不及格学生：skip=%s, limit=%s", skip, limit)
    result, page, page_size, total = statistical_service.get_score_fails(
        skip, limit, db
    )
    return success_page(result, page, page_size, total)


@sta_router.get('/class_avg',
                summary='查询每个班级的每次考试的平均分,从高到低排序')
def get_class_avg(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, default=10),
    db=Depends(get_db)
):
    logger.info("统计-各班级每次考试平均分：skip=%s, limit=%s", skip, limit)
    result, page, page_size, total = statistical_service.get_class_average(
        skip, limit, db
    )
    return success_page(result, page, page_size, total)


@sta_router.get('/tall_sal',
                summary='查询就业表中薪资最高的x个人的姓名，班级和就业时间，就业公司')
def get_tall_sal(
    limit: int = Query(ge=5, default=5),
    db=Depends(get_db)
):
    logger.info("统计-薪资最高的%s人", limit)
    result, page, page_size, total = statistical_service.get_top_salaries(
        limit, db
    )
    return success_page(result, page, page_size, total)


@sta_router.get('/job_time',
                summary='查询每个学生的就业时长（offer下发时间-就业开放时间）')
def get_job_time(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, default=10),
    db=Depends(get_db)
):
    logger.info("统计-各学生就业时长：skip=%s, limit=%s", skip, limit)
    result, page, page_size, total = statistical_service.get_job_durations(
        skip, limit, db
    )
    return success_page(result, page, page_size, total)


@sta_router.get('/avg_class_job_time',
                summary='查询每个班级的平均就业时长')
def get_avg_class_job_time(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, default=10),
    db=Depends(get_db)
):
    logger.info("统计-各班级平均就业时长：skip=%s, limit=%s", skip, limit)
    result, page, page_size, total = statistical_service.get_avg_class_job_time(
        skip, limit, db
    )
    return success_page(result, page, page_size, total)
