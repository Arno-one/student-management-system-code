from model.Student import Student
from sqlalchemy import func
from sqlalchemy.orm import Session
from model.Employment import Employment
from model.Class import Class
from model.Score import Score

# 查询年龄大于30的学⽣
def get_student_ge30(db:Session, skip:int = 0, limit:int = 10):
    user = db.query(Student).filter(
        Student.age >= 30,
        Student.is_deleted == 0
    ).offset(skip).limit(limit).all()
    return user

# 获取年龄>=30的学生总数
def get_student_ge30_count(db:Session):
    count = db.query(Student).filter(
        Student.age >= 30, 
        Student.is_deleted == 0
    ).count()
    return count

# 统计年龄大于30的学⽣的个数、男生的个数、女生的个数
def get_student_count(db:Session):
    all_count = db.query(Student).filter(Student.is_deleted == 0).count()
    man_count = db.query(Student).filter(
        Student.gender == "男",
        Student.is_deleted == 0
    ).count()
    woman_count = db.query(Student).filter(
        Student.gender == "女",
        Student.is_deleted == 0
    ).count()
    return {"全体人数": all_count, "男生人数": man_count, "女生人数": woman_count}

# 统计每次考试都在80分以上的学生信息
def get_score_ge80(db:Session, skip:int = 0, limit:int = 10):
    # 查询考过80分以下的学生编号
    subquery = (db.query(Score.student_no)
                .filter(Score.score < 80, Score.is_deleted == 0)
                .distinct()
                .all())
    filter_no = [s[0] for s in subquery]
    
    # 使用 label 为字段命名，方便转换为字典
    result = (db.query(
                Student.student_no.label('student_no'),
                Student.student_name.label('student_name'),
                Score.score.label('score')
              )
              .join(Score, Score.student_no == Student.student_no)
              .filter(
                  Student.student_no.not_in(filter_no) if filter_no else True,
                  Score.is_deleted == 0,
                  Student.is_deleted == 0
              )
              .order_by(Student.student_no, Score.exam_order)
              .offset(skip).limit(limit).all())
    
    return result

# 查询2次以上不及格的学生信息
def get_score_le60(db:Session, skip:int = 0, limit:int = 10):
    # 查询有2次及以上不及格的学生编号
    query = (db.query(Score.student_no)
             .filter(Score.score < 60, Score.is_deleted == 0)
             .group_by(Score.student_no)
             .having(func.count(Score.id) >= 2)
             .all())
    
    stu_nos = [s[0] for s in query]
    
    if not stu_nos:
        return []
    
    # 查询这些学生的详细成绩信息
    result = (db.query(
                Student.student_no.label('student_no'),
                Student.student_name.label('student_name'),
                Score.score.label('score')
              )
              .join(Score, Score.student_no == Student.student_no)
              .filter(
                  Student.student_no.in_(stu_nos),
                  Student.is_deleted == 0,
                  Score.is_deleted == 0
              )
              .order_by(Student.student_no, Score.exam_order)
              .offset(skip).limit(limit).all())
    
    return result

# 查询每个班级的每次考试的平均分,从高到低排序
def get_class_avg(db:Session):
    result = (db.query(
                Class.name.label('class_name'),
                Score.exam_order.label('exam_order'),
                func.avg(Score.score).label('avg_score')
             )
             .join(Student, Student.class_id == Class.id)
             .join(Score, Score.student_no == Student.student_no)
             .filter(
                 Score.is_deleted == 0,
                 Student.is_deleted == 0,
                 Class.is_deleted == 0
             )
             .group_by(Class.name, Score.exam_order)
             .order_by(func.avg(Score.score).desc())
             .all())
    
    return result

# 查询就业表中薪资最高的5个人的姓名，班级和就业时间，就业公司
def get_tall_sal(db:Session):
    result = (db.query(
                Employment.student_name.label('student_name'),
                Employment.company_name.label('company_name'),
                Employment.offer_send_time.label('offer_send_time'),
                Employment.salary.label('salary'),
                Class.name.label('class_name')
             )
             .join(Class, Class.id == Employment.class_id)
             .filter(
                 Employment.is_deleted == 0,
                 Class.is_deleted == 0
             )
             .order_by(Employment.salary.desc())
             .limit(5)
             .all())
    
    return result

# 查询每个学生的就业时长（offer下发时间-就业开放时间）
def get_job_time(db:Session, skip:int = 0, limit:int = 10):
    result = (db.query(
                Employment.student_name.label('student_name'),
                func.datediff(Employment.offer_send_time, Employment.job_open_time).label('job_duration_days')
              )
              .filter(Employment.is_deleted == 0)
              .offset(skip).limit(limit).all())
    
    return result

# 统计每个班级的平均就业时长（只统计进⼊就业阶段的学⽣，也就是有就业开放时间）
def avg_class_job_time(db:Session, skip:int = 0, limit:int = 10):
    result = (db.query(
                Class.name.label('class_name'),
                func.avg(func.datediff(Employment.offer_send_time, Employment.job_open_time)).label('avg_days')
              )
              .join(Employment, Employment.class_id == Class.id)
              .filter(
                  Employment.job_open_time != None,
                  Employment.is_deleted == 0
              )
              .group_by(Class.name)
              .offset(skip).limit(limit).all())
    return result
