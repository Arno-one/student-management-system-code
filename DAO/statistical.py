from model.Student import Student
from sqlalchemy import func
from sqlalchemy.orm import Session
from model.Class import Class
from model.Score import Score

# 查询年龄大于30的学⽣
def get_student_ge30(db:Session,skip:int = 0,limit:int = 10):
    user= db.query(Student).filter(Student.age>=30,Student.is_deleted ==0).offset(skip).limit(limit).all()
    return user

# 统计年龄大于30的学⽣的个数、男生的个数、女生的个数
def get_student_count(db:Session):
    all_count = db.query(Student).filter(Student.is_deleted ==0).count()
    man_count = db.query(Student).filter(Student.gender == "男",Student.is_deleted ==0).count()
    woman_count = db.query(Student).filter(Student.gender == "女",Student.is_deleted ==0).count()
    return {"全体人数":all_count,"男生人数":man_count,"女生人数":woman_count}

# 统计每次考试都在80分以上的学生信息
def get_score_ge80(db:Session,skip:int = 0,limit:int = 10):
    subquery = db.query(Score.student_no).filter(Score.score <80,Score.is_deleted ==0).distinct.all()  # 查询考过80分以下的人
    filter_no  = [s[0] for s in subquery] # 提取学号
    result = (db.query(Student.student_no,Student.student_name,Score.score)
              .join(Score,Score.student_no == Student.student_no). # 多表联查
               filter(Student.student_no.not_in(filter_no) if filter_no else True,
                      Score.is_deleted == 0,
                      Student.is_deleted == 0)
              .order_by(Student.student_no,Score.exam_order)
              .offset(skip).limit(limit).all())
    return result

# 查询2次以上不及格的学生信息
def get_score_le60(db:Session,skip:int = 0,limit:int = 10):
    query = (db.query(Score.student_no)
             .filter(Score.score < 60,Score.is_deleted ==0)
             .order_by(Score.student_no)
             .having(func.count(Score.id) >=2)
             )
    stu_nos = [s[0] for s in query]
    result = (db.query(Student.student_no,Student.student_name,Score.score)
              .join(Score,Score.student_no==Student.student_no)
              .filter(Student.student_no.in_(stu_nos) if stu_nos else True,
                      Student.is_deleted ==0,
                      Score.is_deleted ==0)
              .order_by(Student.student_no,Score.exam_order)
              .offset(skip).limit(limit).all())
    return result

# 查询每个班级的每次考试的平均分,从高到低排序
def get_class_avg(db:Session):
    result = (db.query(Class.name, Score.exam_order,func.avg(Score.score).label('avg_grade'))
             .join(Student, Student.class_id == Class.id)
             .join(Score, Score.student_no == Student.student_no)
             .filter(Score.is_deleted == 0,
                     Student.is_deleted == 0,
                     Class.is_deleted == 0)
             .group_by(Class.name, Score.exam_order)
             .order_by(func.avg(Score.score).label('avg_grade').desc())
             .all()
             )
    return result
