"""
教师管理Controller层 — MVC中的Controller
只负责HTTP请求/响应处理，不包含业务逻辑
Pydantic Schema已移至 scheme/teacher_scheme.py
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import database
from typing import Literal
from datetime import datetime
from scheme.teacher_scheme import (
    POST_Teacher_Info,
    PUT_Teacher_Info,
)
from scheme.response_scheme import success, success_page
from service import teacher_service
from util.log import get_logger
from util.rbac import require_permission

# 本模块专用 logger，来源标记为 API.teacher_information_API_Router
logger = get_logger(__name__)

teacher_information_router = APIRouter()


@teacher_information_router.get('/teachers/{id}', dependencies=[Depends(require_permission('teacher:view'))])
def get_teacher(id: int, db=Depends(database.get_db)):
    logger.info("按id查询教师：id=%s", id)
    try:
        # 查到教师后统一用 success 封装，返回 {code, message, data}
        result = teacher_service.get_teacher_by_id(id, db)
        return success(result)
    except ValueError as e:
        logger.warning("按id查询教师失败：id=%s, %s", id, e)
        raise HTTPException(status_code=404, detail=str(e))


@teacher_information_router.get('/teachers', dependencies=[Depends(require_permission('teacher:view'))])
def get_teachers(
    name: str | None = None,
    gender: Literal["男", "女"] | None = None,
    title: str | None = None,
    class_id: int | None = None,
    phone: str | None = None,
    email: str | None = None,
    hire_date_start: datetime | None = None,
    hire_date_end: datetime | None = None,
    sort_by: Literal["id", "name", "hire_date", "create_time", "class_id"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    page: int = 1,
    page_size: int = 20,
    db=Depends(database.get_db),
):
    logger.info("查询教师列表：name=%s, class_id=%s, page=%s, page_size=%s",
                name, class_id, page, page_size)
    result = teacher_service.search_teachers(
        db=db,
        name=name,
        gender=gender,
        title=title,
        class_id=class_id,
        phone=phone,
        email=email,
        hire_date_start=hire_date_start,
        hire_date_end=hire_date_end,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    # service 返回 dict（含 items/total/page/page_size），统一用 success_page 封装分页结果
    return success_page(
        result["items"], result["page"], result["page_size"], result["total"]
    )


@teacher_information_router.post('/teacher', dependencies=[Depends(require_permission('teacher:create'))])
def post_one_teacher(
    teacher: POST_Teacher_Info,
    db=Depends(database.get_db)
):
    """
    新增单个教师（推荐：日常一位一位地加，前端直接填表单提交即可）。
    比起原来必须手写 JSON 数组，单条新增更贴合"录入一位新老师"的真实场景。
    """
    logger.info("新增单个教师：name=%s", teacher.name)
    try:
        teacher_service.create_single_teacher(teacher, db)
        logger.info("新增单个教师成功：name=%s", teacher.name)
        return success(None, '创建成功')
    except Exception as e:
        logger.exception("新增单个教师异常：name=%s, %s", teacher.name, e)
        raise HTTPException(status_code=500, detail=str(e))


@teacher_information_router.get('/teachers/import/template', dependencies=[Depends(require_permission('teacher:import'))])
def download_import_template():
    """
    下载"教师批量导入"的标准 Excel 模板。
    使用者下载 → 按列填好 → 再通过 /teachers/import 上传，整个流程像填表一样直观。
    """
    logger.info("下载教师导入模板")
    bio = teacher_service.build_import_template()
    # Content-Disposition 让浏览器以"下载文件"方式处理，文件名用 ASCII 避免中文乱码
    headers = {"Content-Disposition": "attachment; filename=teacher_import_template.xlsx"}
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@teacher_information_router.post('/teachers/import', dependencies=[Depends(require_permission('teacher:import'))])
async def import_teachers(
    file: UploadFile = File(...),
    db=Depends(database.get_db)
):
    """
    批量导入教师（推荐：通过上传 Excel/CSV 文件一次性录入多位老师）。
    相比原来贴 JSON 数组，上传表格才是教务/HR 真实在用的方式：
    逐行校验，合格的入库、不合格的跳过并返回具体原因，导入结果一目了然。
    """
    logger.info("批量导入教师：文件名=%s", file.filename)
    try:
        content = await file.read()
        result = teacher_service.import_teachers_from_file(content, file.filename, db)
        msg = f"导入完成：成功 {result['success_count']} 条，失败 {result['fail_count']} 条"
        logger.info("批量导入教师成功：%s", msg)
        return success(result, msg)
    except ValueError as e:
        # 文件格式不对 / 表头缺列等"使用者可纠正"的问题，返回 400 提示
        logger.warning("批量导入教师参数错误：%s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("批量导入教师异常：%s", e)
        raise HTTPException(status_code=500, detail=str(e))


@teacher_information_router.post('/teachers', dependencies=[Depends(require_permission('teacher:create'))])
def post_teachers(
    temp_new_teachers: list[POST_Teacher_Info],
    db=Depends(database.get_db)
):
    """（保留）原始的 JSON 数组批量创建，仅作兼容；新场景请用 /teacher 或 /teachers/import"""
    logger.info("批量创建教师：共 %s 条", len(temp_new_teachers))
    try:
        teacher_service.create_teachers(temp_new_teachers, db)
        logger.info("批量创建教师成功：共 %s 条", len(temp_new_teachers))
        return success(None, '创建成功')
    except Exception as e:
        # 这里捕获的是宽泛 Exception，可能是程序异常，记完整堆栈进 error.log
        logger.exception("批量创建教师异常：%s", e)
        raise HTTPException(status_code=500, detail=str(e))


@teacher_information_router.put('/teachers/{id}', dependencies=[Depends(require_permission('teacher:update'))])
def put_teacher(
    id: int,
    temp_teacher_update_info: PUT_Teacher_Info,
    db=Depends(database.get_db)
):
    logger.info("更新教师：id=%s", id)
    try:
        teacher_service.update_teacher(id, temp_teacher_update_info, db)
        logger.info("更新教师成功：id=%s", id)
        return success(None, '更新成功')
    except Exception as e:
        logger.exception("更新教师异常：id=%s, %s", id, e)
        raise HTTPException(status_code=400, detail=str(e))
