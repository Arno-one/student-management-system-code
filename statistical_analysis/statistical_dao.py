from model.student import Student
from sqlalchemy.orm import Session
from model.Score import Score

# 查询年龄大于30的学⽣
def get_student_ge30(db:Session,skip:int = 0,limit:int = 10):
    user= db.query(Student).filter(Student.age>=30).offset(skip).limit(limit).all()
    return user

# 统计年龄大于30的学⽣的个数、男生的个数、女生的个数
def get_student_count(db:Session):
    all_count = db.query(Student).count()
    man_count = db.query(Student).filter(Student.gender == "男")
    woman_count = db.query(Student).filter(Student.gender == "女")
    return {"全体人数":all_count,"男生人数":man_count,"女生人数":woman_count}

def get_score_ge80(db:Session,skip:int = 0,limit:int = 10):
    user =db.query(Score).filter(Score.score >80).having(Score.exam_order).offset(skip).limit(limit).all()
