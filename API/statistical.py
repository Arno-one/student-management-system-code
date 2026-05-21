from fastapi import APIRouter, Depends, Query
from typing import List
from database import get_db
from DAO import statistical
from scheme.statistical_request import (
    StudentGe30Response,
    StudentCountResponse,
    ScoreGe80Response,
    ScoreLe60Response,
    ClassAvgResponse,
    TallSalResponse,
    JobTimeResponse,
    AvgClassJobTimeResponse,
    PageResponse
)

sta_router = APIRouter()


@sta_router.get('/ge_stu',
                description='查询年龄大于xx的学⽣',
                response_model=PageResponse[StudentGe30Response])
def get_student_age(skip: int=Query(min=0), limit: int=Query(min=10), age :int =Query(min=0),db=Depends(get_db)):
    result = statistical.get_student_age(db, skip, age,limit)
    total = statistical.get_student_age_count(db, age)
    return PageResponse(
        code=200,
        data=result,
        page=skip // limit + 1 if limit > 0 else 1,
        total=total)


@sta_router.get('/stu_count',
                description='统计学生人数',
                response_model=StudentCountResponse)
def get_student_count(db=Depends(get_db)):
    result = statistical.get_student_count(db)
    return result


@sta_router.get('/score_greater',
                description='查询每次考试都在xx分以上的学生信息',
                response_model=PageResponse[ScoreGe80Response])
def get_score_grade(skip: int=Query(min=0), limit: int=Query(min=10), grade:int=Query(min=0),db=Depends(get_db)):
    result = statistical.get_score_grade(db, skip, grade,limit)
    total  = statistical.get_score_grade_count(db, grade)
    return PageResponse(
        code=200,
        data=result,
        page=skip // limit + 1 if limit > 0 else 1,
        total=total)


@sta_router.get('/score_fails',
                description='查询2次以上不及格学生的信息',
                response_model=PageResponse[ScoreLe60Response])
def get_score_fails(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.get_score_le60(db, skip, limit)

    return PageResponse(
        code=200,
        data=result,
        page=skip // limit + 1 if limit > 0 else 1,
        total=len(result))


@sta_router.get('/class_avg',
                description='查询每个班级的每次考试的平均分,从高到低排序',
                response_model=PageResponse[ClassAvgResponse])
def get_class_avg(db=Depends(get_db)):
    result = statistical.get_class_avg(db)

    return PageResponse(
        code=200,
        data=result,
        page=1,
        total=len(result))


@sta_router.get('/tall_sal',
                description='查询就业表中薪资最高的x个人的姓名，班级和就业时间，就业公司',
                response_model=PageResponse[TallSalResponse])
def get_tall_sal(limit :int =Query(min=5),db=Depends(get_db)):
    result = statistical.get_tall_sal(db,limit)

    return PageResponse(
        code=200,
        data=result,
        page=1,
        total=len(result))


@sta_router.get('/job_time',
                description='查询每个学生的就业时长（offer下发时间-就业开放时间）',
                response_model=PageResponse[JobTimeResponse])
def get_job_time(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.get_job_time(db, skip, limit)

    return PageResponse(
        code=200,
        data=result,
        page=skip // limit + 1 if limit > 0 else 1,
        total=len(result))


@sta_router.get('/avg_class_job_time',
                description='查询每个班级的平均就业时长',
                response_model=PageResponse[AvgClassJobTimeResponse])
def get_avg_class_job_time(skip: int = Query(min=0), limit: int = Query(min=10), db = Depends(get_db)):
    result = statistical.avg_class_job_time(db, skip, limit)
    total = statistical.get_avg_class_job_time_count(db)

    return PageResponse(
        code=200,
        data=result,
        page=skip // limit + 1 if limit > 0 else 1,
        total=total
    )
