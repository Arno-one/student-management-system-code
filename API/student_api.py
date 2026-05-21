from fastapi import APIRouter,Depends,HTTPException,Path,Query
from sqlalchemy.orm import Session
from DAO import student_dao

# 获取数据库db连接
from database import get_db
# Pydantic 模型（请求体、响应体）
from scheme.student_scheme import (StudentCreate,StudentUpdate)

# 创建路由器
student_router = APIRouter()

@student_router.post("/students", response_model=StudentCreate, summary="创建学生")

def create_student(
        student_data: StudentCreate,  # 接收前端传的JSON，自动校验格式
        db: Session = Depends(get_db)  # 依赖注入：获取数据库会话
):

    # 检查学号是否已存在
    existing = student_dao.get_by_student_no(student_data.student_no,db)
    if existing:
        raise HTTPException(status_code=400, detail=f"学号 {student_data.student_no} 已存在")

    try:
        # 过滤掉 None 值
        create_data = {k: v for k, v in student_data.dict().items() if v is not None}
        student = student_dao.create_from_dict(create_data,db)
        return student
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@student_router.get("/students", summary="查询所有学生信息")
def get_all_students(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        db: Session = Depends(get_db)
):
    """分页查询所有学生信息"""
    students = student_dao.get_all(skip, limit, db)
    page = skip // limit + 1 if limit > 0 else 1
    total = student_dao.count(db)

    return {
        "code": 200,
        "message": "success",
        "data": students,
        "page": page,
        "total": total
    }


@student_router.get("/students/{student_id}",summary="根据ID查询学生")
def get_student_by_id(
        student_id: int = Path(..., ge=1, le=999999),
        db: Session = Depends(get_db)
):
    """根据学生ID查询详细信息"""
    student = student_dao.get_by_id(student_id,db)

    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在")

    return {"code":200,"message":"success","data":student}


@student_router.get("/students/no/{student_no}", summary="根据学号查询学生")
def get_student_by_no(
        student_no: str,
        db: Session = Depends(get_db)
):
    """根据学号查询学生信息"""
    student = student_dao.get_by_student_no(student_no,db)

    if not student:
        raise HTTPException(status_code=404, detail=f"学号 {student_no} 不存在")

    return {"code":200,"message":"success","data":student}

@student_router.get("/students/class/{class_id}", summary="根据班级查询")
def get_students_by_class(
        class_id: int = Path(..., ge=1),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        db: Session = Depends(get_db)

):
    """查询指定班级的所有学生"""
    result = student_dao.get_by_class(skip,limit,class_id,db)
    total = student_dao.get_by_class_count(class_id,db)
    page = skip // limit +1 if limit >0  else 1
    return {"code":200,"message":"success","data":result,"page":page,"total":total}


@student_router.patch("/students/{student_id}", response_model=StudentUpdate,summary="更新学生信息（只改提供的字段）")
def update_student(
        update_data: StudentUpdate,
        student_id: int = Path(..., ge=1, le=999999),
        db: Session = Depends(get_db)
):
    """更新学生信息（只更新提供的字段）"""
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")

    student = student_dao.update(student_id, update_dict,db)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在")

    return student


@student_router.delete("/students/{student_id}", summary="逻辑删除学生")
def delete_student(
        student_id: int = Path(..., ge=1, le=999999),
        db: Session = Depends(get_db)
):
    """逻辑删除学生（is_deleted 设为 1）"""
    # dao = StudentDAO(db)

    # 先检查学生是否存在且未删除
    student = student_dao.get_by_id(student_id,db)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在或已删除")

    success = student_dao.soft_delete(student_id,db)
    if success:
        return {"code":200,"message":"删除成功"}
    else:
        raise HTTPException(status_code=500, detail="删除失败")


@student_router.post("/students/{student_id}/restore", summary="恢复已删除学生")
def restore_student(
        student_id: int = Path(..., ge=1, le=999999),
        db: Session = Depends(get_db)
):
    """恢复已逻辑删除的学生（is_deleted 设为 0）"""
    success = student_dao.restore(student_id,db)
    if success:
        return {"code":200,"message":"恢复成功"}
    else:
        raise HTTPException(status_code=404, detail=f"未找到已删除的学生ID {student_id}")