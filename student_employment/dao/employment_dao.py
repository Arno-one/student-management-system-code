from sqlalchemy.orm import Session
from student_employment.model.employment_model import Employment
from student_employment.scheme.employment_scheme import EmploymentCreate,EmploymentUpdate
from datetime import datetime

#新建就业信息
def create_employment(db: Session,data:EmploymentCreate):
    emp = Employment(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

#根据id查询
def get_employment_by_id(db: Session,emp_id:int):
    return db.query(Employment).filter(
        Employment.id==emp_id,
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
def get_employment_list(
        db: Session,
        page:int=1,
        size:int=5,
        student_name:str=None,
        class_id:int=None,
        company_name:str=None
):
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
    return emp


#逻辑删除
def delete_employment(db: Session,emp):
    emp.is_deleted = 1
    emp.delete_time = datetime.now()
    db.commit()
    return {"删除成功"}

#逻辑恢复
def recover_employment(db: Session,emp):
    emp.is_deleted = 0
    db.commit()
    db.refresh(emp)
    return {"message":"恢复成功","data":emp}

#物理删除
def hard_delete_employment(db: Session,emp):
    db.delete(emp)
    db.commit()
    return {"message":"删除成功"}





