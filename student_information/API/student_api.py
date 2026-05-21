from fastapi import APIRouter,Depends,HTTPException,Query,Body,Path
from sqlalchemy.orm import Session
from typing import Optional,List

# 获取数据库db连接
from database import get_db
from student_information.Dao.student_dao import StudentDAO
# Pydantic 模型（请求体、响应体）
from student_information.scheme.student_scheme import (StudentCreate,StudentUpdate,StudentResponse,ApiResponse)

# 创建路由器
router = APIRouter(prefix="/students",tags=["学生管理"])

# ==================== 新增学生 ====================
@router.post("", response_model=ApiResponse, summary="创建学生")
# ApiResponse 是在student_scheme.py中自定义的统一响应模型，用来让所有接口都返回统一格式
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

    # 实例化一个 StudentDAO 的对象 dao，外部传进来的 db 变成 StudentDAO 实例的属性，供内部方法使用
    dao = StudentDAO(db)

    # 检查学号是否已存在
    existing = dao.get_by_student_no(student_data.student_no)
    if existing:
        raise HTTPException(status_code=400, detail=f"学号 {student_data.student_no} 已存在")

    try:
        # 过滤掉 None 值
        create_data = {k: v for k, v in student_data.dict().items() if v is not None}
        student = dao.create_from_dict(create_data)
        return ApiResponse(code=200, message="创建成功", data=StudentResponse.model_validate(student))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

# ==================== 批量逻辑删除 ====================
@router.delete("/batch", response_model=ApiResponse, summary="批量逻辑删除")
def batch_delete_students(
        student_ids: List[int] = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    """批量逻辑删除学生"""
    dao = StudentDAO(db)

    try:
        deleted_count = dao.batch_soft_delete(student_ids)
        return ApiResponse(
            code=200,
            message=f"成功删除 {deleted_count} 名学生",
            data={"deleted_count": deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


# ==================== 查询学生 ====================
@router.get("/{student_id}", response_model=ApiResponse, summary="根据ID查询学生")
def get_student_by_id(
        student_id: int= Path(..., ge=1, le=999999, description="学生ID"),  # 加上校验
        db: Session = Depends(get_db)
):
    """根据学生ID查询详细信息"""
    dao = StudentDAO(db)
    student = dao.get_by_id(student_id)

    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在")

    return ApiResponse(code=200, data=StudentResponse.model_validate(student))


@router.get("/no/{student_no}", response_model=ApiResponse, summary="根据学号查询学生")
def get_student_by_no(
        student_no: str,
        db: Session = Depends(get_db)
):
    """根据学号查询学生信息"""
    dao = StudentDAO(db)
    student = dao.get_by_student_no(student_no)

    if not student:
        raise HTTPException(status_code=404, detail=f"学号 {student_no} 不存在")

    return ApiResponse(code=200, data=StudentResponse.model_validate(student))


@router.get("", response_model=ApiResponse, summary="查询学生列表")
def list_students(
        page: int = Query(0, ge=0, description="页数"),
        limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
        student_name: Optional[str] = Query(None, description="学生姓名（模糊查询）"),
        gender: Optional[str] = Query(None, description="性别"),
        class_id: Optional[int] = Query(None, description="班级ID"),
        min_age: Optional[int] = Query(None, ge=0, description="最小年龄"),
        max_age: Optional[int] = Query(None, ge=0, description="最大年龄"),
        education: Optional[str] = Query(None, description="学历"),
        db: Session = Depends(get_db)
):
    """
    查询学生列表，支持多条件筛选和分页
    """
    dao = StudentDAO(db)

    # 如果有查询条件，使用搜索方法
    if any([student_name, gender, class_id, min_age, max_age, education]):
        students = dao.search(
            student_name=student_name,
            gender=gender,
            class_id=class_id,
            min_age=min_age,
            max_age=max_age,
            education=education
        )
        total = len(students)
        students = students[page:page + limit]
    else:
        students = dao.get_all(page=page-1, limit=limit)
        # total = dao.count()
        total = len(students)
    data = [StudentResponse.model_validate(student) for student in students]
    return ApiResponse(code=200, data=data, total=total , page=page, limit=limit)


@router.get("/class/{class_id}", response_model=ApiResponse, summary="根据班级查询")
def get_students_by_class(
        class_id: int,
        db: Session = Depends(get_db)
):
    """查询指定班级的所有学生"""
    dao = StudentDAO(db)
    students = dao.get_by_class(class_id)
    data = [StudentResponse.model_validate(student) for student in students]
    return ApiResponse(code=200, data=data, total=len(students))


# ==================== 更新学生 ====================
@router.patch("/{student_id}", response_model=ApiResponse, summary="更新学生信息（只改提供的字段）")
def update_student(
        student_id: int,
        update_data: StudentUpdate,
        db: Session = Depends(get_db)
):
    """更新学生信息（只更新提供的字段）"""
    dao = StudentDAO(db)

    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")

    student = dao.update(student_id, update_dict)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在")

    return ApiResponse(
        code=200,
        message="更新成功",
        data=StudentResponse.model_validate(student)
    )



# ==================== 逻辑删除 ====================
@router.delete("/{student_id}", response_model=ApiResponse, summary="逻辑删除学生")
def delete_student(
        student_id: int,
        db: Session = Depends(get_db)
):
    """逻辑删除学生（is_deleted 设为 1）"""
    dao = StudentDAO(db)

    # 先检查学生是否存在且未删除
    student = dao.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生ID {student_id} 不存在或已删除")

    success = dao.soft_delete(student_id)
    if success:
        return ApiResponse(code=200, message="删除成功")
    else:
        raise HTTPException(status_code=500, detail="删除失败")


# @router.delete("/batch", response_model=ApiResponse, summary="批量逻辑删除")
# def batch_delete_students(
#         student_ids: List[int] = Body(..., embed=True),
#         db: Session = Depends(get_db)
# ):
#     """批量逻辑删除学生"""
#     dao = StudentDAO(db)
#
#     try:
#         deleted_count = dao.batch_soft_delete(student_ids)
#         return ApiResponse(
#             code=200,
#             message=f"成功删除 {deleted_count} 名学生",
#             data={"deleted_count": deleted_count}
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.post("/{student_id}/restore", response_model=ApiResponse, summary="恢复已删除学生")
def restore_student(
        student_id: int,
        db: Session = Depends(get_db)
):
    """恢复已逻辑删除的学生（is_deleted 设为 0）"""
    dao = StudentDAO(db)

    success = dao.restore(student_id)
    if success:
        return ApiResponse(code=200, message="恢复成功")
    else:
        raise HTTPException(status_code=404, detail=f"未找到已删除的学生ID {student_id}")