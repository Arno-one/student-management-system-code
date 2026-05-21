from fastapi import Depends, HTTPException, APIRouter, Query
from sqlalchemy.orm import Session
from database import get_db
from student_employment.dao import employment_dao as dao
from student_employment.scheme import employment_scheme as EMP

router = APIRouter()

#创建就业信息
@router.post("/employment_create",response_model=EMP.EmploymentResponse,summary="新建学生就业信息")
def employment_create(
        data:EMP.EmploymentCreate,
        db: Session = Depends(get_db)
):
    emp = dao.get_employment_by_student_no(db,data.student_no)
    if emp:
        raise HTTPException(status_code=409,detail="就业信息已存在")
    return dao.create_employment(db,data)

#根据id查询
@router.get("/employment_get/{emp_id}",response_model=EMP.EmploymentResponse,summary="根据id查询")
def employment_get(emp_id:int,db: Session = Depends(get_db)):
    emp = dao.get_employment_by_id(db,emp_id)
    if not emp:
        raise HTTPException(status_code=404,detail="就业信息不存在")
    return emp

#分页查询列表
@router.get("/employment_list",summary="分页查询")
def get_employment_list(
        page:int = Query(1, ge=1),
        size:int = Query(10, le=100, ge=1),
        student_name:str=None,
        class_id:int=None,
        company_name:str=None,
        db: Session = Depends(get_db)
):
    return dao.get_employment_list(db,page,size,student_name,class_id,company_name)

#修改就业信息
@router.put("/employment_update/{emp_id}",response_model=EMP.EmploymentResponse,summary="修改就业信息")
def employment_update(
        emp_id:int,
        data:EMP.EmploymentUpdate,
        db: Session = Depends(get_db)
):
    emp = dao.get_employment_by_id(db,emp_id)
    if not emp:
        raise HTTPException(status_code=404,detail="就业信息不存在")
    new_emp = None
    if data.student_no:#校验学生编号是否占用
        new_emp = dao.check_student_no(db,emp_id,data)
    if new_emp:
        raise HTTPException(status_code=409, detail="学生编号已存在")
    return dao.update_employment(db,emp,data)

#逻辑删除
@router.delete("/employment_delete/{emp_id}",summary="逻辑删除")
def employment_delete(emp_id:int,db: Session = Depends(get_db)):
    emp = dao.get_employment_by_id(db,emp_id)
    if not emp:
        raise HTTPException(status_code=404,detail="就业信息不存在")
    return dao.delete_employment(db,emp)

#逻辑恢复
@router.put("/employment_recover/{emp_id}",summary="逻辑恢复")
def employment_recover(emp_id:int,db: Session = Depends(get_db)):
    emp = dao.get_employment_id_all(db,emp_id)
    if not emp:
        raise HTTPException(status_code=404,detail="就业信息不存在")
    if emp.is_deleted == 0:
        raise HTTPException(status_code=409,detail="数据无需恢复")
    return dao.recover_employment(db,emp)

#物理删除
@router.delete("/employment_hard/{emp_id}",summary="物理删除")
def employment_hard(emp_id:int,db: Session = Depends(get_db)):
    emp = dao.get_employment_id_all(db,emp_id)
    if not emp:
        raise HTTPException(status_code=404,detail="就业信息不存在")
    return dao.hard_delete_employment(db,emp)

