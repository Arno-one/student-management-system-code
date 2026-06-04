from sqlalchemy.orm import Session
from model.Employment import Employment
from scheme.employment_scheme import EmploymentCreate,EmploymentUpdate
from datetime import datetime
from util.log import get_logger

# 本模块专用 logger，来源标记为 DAO.employment_dao
logger = get_logger(__name__)

#新建就业信息
def create_employment(db: Session,data:EmploymentCreate):
    emp = Employment(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    logger.info("就业信息已入库（事务已提交）：id=%s, student_no=%s", emp.id, emp.student_no)
    return emp

#根据id查询
def get_employment_by_id(db: Session,emp_id:int):
    return db.query(Employment).filter(
        Employment.id== emp_id,
        Employment.is_deleted == 0
    ).first()

#根据id查所有
def get_employment_id_all(db: Session,emp_id:int):
    return db.query(Employment).filter(
        Employment.id==emp_id,
    ).first()

#根据学号查询
def get_employment_by_student_no(db: Session,student_no:str):
    return db.query(Employment).filter(
        Employment.student_no==student_no,
        Employment.is_deleted == 0
    ).first()

#校验学生编号是否占用
def check_student_no(db: Session,emp_id:int,data):
    return ((db.query(Employment).filter(Employment.student_no == data.student_no))
            .filter(Employment.id != emp_id)).first()

#分页查询
def get_employment_list(db: Session,page:int,size:int,student_name:str,class_id:int,company_name:str):
    skip = (page-1)*size
    query = db.query(Employment).filter(Employment.is_deleted == 0)
    if student_name:
        query = query.filter(Employment.student_name.like(f"%{student_name}%"))
    if class_id:
        query = query.filter(Employment.class_id == class_id)
    if company_name:
        query = query.filter(Employment.company_name.like(f"%{company_name}%"))
    total = query.count()
    items = query.order_by(Employment.id.asc()).offset(skip).limit(size).all()
    return{
        "list":items,
        "total":total,
        "page":page,
        "size":size
    }

#更新就业信息
def update_employment(db: Session,emp,data:EmploymentUpdate):
    update_data = data.model_dump(exclude_unset=True)
    for k,v in update_data.items():
        setattr(emp,k,v)
    emp.update_time = datetime.now()
    db.commit()
    db.refresh(emp)
    logger.info("就业信息已更新（事务已提交）：id=%s, 字段=%s", emp.id, list(update_data.keys()))
    return emp


#逻辑删除
def delete_employment(db: Session,emp):
    emp.is_deleted = 1
    emp.delete_time = datetime.now()
    db.commit()
    logger.info("就业信息已逻辑删除（事务已提交）：id=%s", emp.id)
    return {"删除成功"}

#逻辑恢复
def recover_employment(db: Session,emp):
    emp.is_deleted = 0
    db.commit()
    db.refresh(emp)
    logger.info("就业信息已恢复（事务已提交）：id=%s", emp.id)
    return {"message":"恢复成功","data":emp}

#物理删除
def hard_delete_employment(db: Session,emp):
    # 物理删除不可恢复，用 warning 级别留个醒目记录
    logger.warning("就业信息物理删除（不可恢复，事务即将提交）：id=%s", emp.id)
    db.delete(emp)
    db.commit()
    return {"message":"删除成功"}





