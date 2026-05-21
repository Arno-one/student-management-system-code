from fastapi import APIRouter,Depends,HTTPException,Path,Query
from sqlalchemy.orm import Session
from student_information.Dao import student_dao

# 获取数据库db连接
from database import get_db
# Pydantic 模型（请求体、响应体）
from student_information.scheme.student_scheme import (StudentCreate,StudentUpdate)

# 创建路由器
student_router = APIRouter(prefix="/students",tags=["学生管理"])

# ==================== 新增学生 ====================
@student_router.post("", response_model=StudentCreate, summary="创建学生")

def create_student(
        student_data: StudentCreate,  # 接收前端传的JSON，自动校验格式
        db: Session = Depends(get_db)  # 依赖注入：获取数据库会话
):
    """
    创建单个学生

    - **student_no**: 学号（唯一）
    - **class_id**: 班级ID
    - **student_name**: 学生姓名
    - 其他字段可选
    """

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


# ==================== 查询学生 ====================
@student_router.get("/{student_id}",summary="根据ID查询学生")
def get_student_by_id(
        student_id: int = Path(..., ge=1, le=999999),
        db: Session = Depends(get_db)
):
    """根据学生ID查询详细信息"""
    student = student_dao.get_by_id(student_id,db)

    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在")

    return {"code":200,"message":"success","data":student}


@student_router.get("/no/{student_no}", summary="根据学号查询学生")
def get_student_by_no(
        student_no: str,
        db: Session = Depends(get_db)
):
    """根据学号查询学生信息"""
    student = student_dao.get_by_student_no(student_no,db)

    if not student:
        raise HTTPException(status_code=404, detail=f"学号 {student_no} 不存在")

    return {"code":200,"message":"success","data":student}

@student_router.get("/class/{class_id}", summary="根据班级查询")
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


# ==================== 更新学生 ====================
@student_router.patch("/{student_id}", response_model=StudentUpdate,summary="更新学生信息（只改提供的字段）")
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


# ==================== 逻辑删除 ====================
@student_router.delete("/{student_id}", summary="逻辑删除学生")
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


@student_router.post("/{student_id}/restore", summary="恢复已删除学生")
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