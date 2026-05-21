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
    AvgClassJobTimeResponse
)

sta_router = APIRouter()


@sta_router.get('/ge_stu',
                description='查询年龄大于30的学⽣',
                response_model=List[StudentGe30Response])
def get_student_ge30(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.get_student_ge30(db, skip, limit)
    return result


@sta_router.get('/stu_count',
                description='统计学生人数',
                response_model=StudentCountResponse)
def get_student_count(db=Depends(get_db)):
    result = statistical.get_student_count(db)
    return result


@sta_router.get('/score_ge80',
                description='查询每次考试都在80分以上的学生信息',
                response_model=List[ScoreGe80Response])
def get_score_ge80(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.get_score_ge80(db, skip, limit)

    return result


@sta_router.get('/score_le60',
                description='查询2次以上不及格学生的信息',
                response_model=List[ScoreLe60Response])
def get_score_le60(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.get_score_le60(db, skip, limit)

    return result


@sta_router.get('/class_avg',
                description='查询每个班级的每次考试的平均分,从高到低排序',
                response_model=List[ClassAvgResponse])
def get_class_avg(db=Depends(get_db)):
    result = statistical.get_class_avg(db)

    return result


@sta_router.get('/tall_sal',
                description='查询就业表中薪资最高的5个人的姓名，班级和就业时间，就业公司',
                response_model=List[TallSalResponse])
def get_tall_sal(db=Depends(get_db)):
    result = statistical.get_tall_sal(db)

    return result


@sta_router.get('/job_time',
                description='查询每个学生的就业时长（offer下发时间-就业开放时间）',
                response_model=List[JobTimeResponse])
def get_job_time(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.get_job_time(db, skip, limit)

    return result


@sta_router.get('/avg_class_job_time',
                description='查询每个班级的平均就业时长',
                response_model=List[AvgClassJobTimeResponse])
def get_avg_class_job_time(skip: int=Query(min=0), limit: int=Query(min=10), db=Depends(get_db)):
    result = statistical.avg_class_job_time(db, skip, limit)

    return result
