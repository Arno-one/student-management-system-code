
from sqlalchemy.orm import Session
from model.Score import Score
from model.Student import Student
from decimal import Decimal
from typing import List
from util.log import get_logger

# 本模块专用 logger，来源标记为 DAO.score_dao
logger = get_logger(__name__)


#查询
def query_score(
    db: Session,
    page: int = 1,   #页码
    page_size: int = 10 ,   #每页的数量
    student_no: str | None = None,  #学生编号
    exam_order: int | None= None,  #考试次序
    class_id : int | None = None,  #班级id
    min_score: Decimal |None = None,  #最低成绩
    max_score: Decimal | None= None,    #最高成绩
    sort_no : str | None = None,   #按学号排序
    sort_by_score : str | None = None  #按成绩排序

):
    #先查全部数据,同时关联Student表
    q = db.query(Score).join(Student, Score.student_no == Student.student_no)
    # 只查未删除的数据
    q = query_not_deleted(q)
    #按编号查询
    q = query_student_no(q,student_no)
    #按考试序次查询
    q = query_exam_order(q,exam_order)
    #范围查询--最低
    q = query_score_min(q,min_score)
    #范围查询--最高
    q = query_score_max(q,max_score)
    #按班级筛选
    q = query_class_id(q,class_id)
    #学号排序
    q = sort_student_no(q,sort_no)
    #分数排序
    q = sort_score(q,sort_by_score)
    #分页查询
    offset = (page - 1) * page_size
    data_list = q.offset(offset).limit(page_size).all()

    return data_list


#统计符合条件的成绩总条数（独立方法，不改 query_score 签名，专门给分页算 total 用）
def count_score(
    db: Session,
    student_no: str | None = None,  #学生编号
    exam_order: int | None = None,  #考试次序
    class_id: int | None = None,  #班级id
    min_score: Decimal | None = None,  #最低成绩
    max_score: Decimal | None = None,  #最高成绩
):
    #和 query_score 用同一套筛选条件，但不分页、不排序，只取总数
    q = db.query(Score).join(Student, Score.student_no == Student.student_no)
    q = query_not_deleted(q)
    q = query_student_no(q, student_no)
    q = query_exam_order(q, exam_order)
    q = query_score_min(q, min_score)
    q = query_score_max(q, max_score)
    q = query_class_id(q, class_id)
    #返回满足条件的总行数
    return q.count()


#只未删除数据
def query_not_deleted(q):
    return q.filter(Score.is_deleted == 0)


#按学生编号筛选
def query_student_no(q,student_no):
    if student_no:
        q = q.filter(Score.student_no == student_no)
    return q
#按班级筛选
def query_class_id(q,class_id):
    if class_id:
        q = q.filter(Student.class_id == class_id)
    return q


#按考试次序筛选
def query_exam_order(q,exam_order):
    if exam_order:
        q = q.filter(Score.exam_order == exam_order)
    return q

#按分数范围筛选
#最小范围
def query_score_min(q,min_score):
    if min_score:
        q = q.filter(Score.score >= min_score)
    return q
#最大范围
def query_score_max(q,max_score)  :
    if max_score:
        q = q.filter(Score.score <= max_score)
    return q

# #按 是否修改过 筛选
# def query_modified_status(q,update):
#     if update is False:
#         q = q.filter(Score.create_time == Score.update_time)
#     elif update is True:
#         q = q.filter(Score.create_time != Score.update_time)
#     return q

#学生编号排序
def sort_student_no(q,sort_no):
    # 升序
    if sort_no == "asc":
        q = q.order_by(Score.student_no.asc())
    # 降序
    elif sort_no == "desc":
        q = q.order_by(Score.student_no.desc())

    return q
#成绩排序
def sort_score(q,score):
    # 升序
    if score == "asc":
        q = q.order_by(Score.score.asc())
    # 降序
    elif score == "desc":
        q = q.order_by(Score.score.desc())

    return q





# 查询学生成绩是否存在数据库中,如果没找到就说明没在
def is_exist(db: Session, student_no: str, exam_order: int):
    result = db.query(Score).filter(
        Score.student_no == student_no,
        Score.exam_order == exam_order,
        Score.is_deleted == 0
    ).first()
    #返回查询到的结果
    return result

#新增成绩
def add_score(db:Session,new_score):
    #插入单个成绩
    db.add(new_score)
    db.commit()
    db.refresh(new_score)
    logger.info("成绩已入库（事务已提交）：student_no=%s, exam_order=%s",
                new_score.student_no, new_score.exam_order)
    #返回插入的成绩
    return new_score

#批量新增
def batch_add_scores(db: Session, batch_data: List[Score]):
    # 直接批量插入
    db.add_all(batch_data)
    db.commit()
    # 批量提交是关键节点，记录实际写入条数
    logger.info("成绩批量入库（事务已提交）：共 %s 条", len(batch_data))
    # 返回处理好的数据
    return batch_data




#更新学生成绩
def update_score(db:Session,student_no:str,exam_order:int,score:Decimal):
    result = is_exist(db,student_no, exam_order)
    result.score = score
    db.commit()
    db.refresh(result)
    logger.info("成绩已更新（事务已提交）：student_no=%s, exam_order=%s, score=%s",
                student_no, exam_order, score)
    return result


#逻辑删除
def is_delete(db:Session,student_no:str,exam_order:int):
    result = db.query(Score).filter(Score.student_no == student_no,
                                    Score.exam_order == exam_order,
                                    Score.is_deleted == 0).first()
    result.is_deleted = 1
    db.commit()
    db.refresh(result)
    logger.info("成绩已逻辑删除（事务已提交）：student_no=%s, exam_order=%s",
                student_no, exam_order)
    return result


#删除数据
# def del_score(db:Session,student_no:str,exam_order:int):
#     # 先判断学生成绩信息是否存在
#     result = db.query(Score).filter(Score.student_no == student_no,
#                                     Score.exam_order == exam_order,
#                                     Score.is_deleted == 0).first()
#     db.delete(result)
#     db.commit()
#     return result



