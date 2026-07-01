"""
学生管理Controller层 — MVC中的Controller
只负责HTTP请求/响应处理，不包含业务逻辑
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from database import get_db
from scheme.student_scheme import StudentCreate, StudentUpdate, StudentExtract, StudentUpdateExtract
from scheme.response_scheme import success, success_page
from service import student_service, extract_service
from DAO.student_dao import get_by_student_no
from util.log import get_logger
from util.rbac import require_permission

# 本模块专用 logger，日志里会显示来源是 API.student_api，方便定位
logger = get_logger(__name__)

student_router = APIRouter()


class NLExtractRequest(BaseModel):
    """自然语言提取请求"""
    text: str = Field(..., description="自然语言描述", min_length=1, max_length=2000)


# StudentCreate 中的必填字段名
_STUDENT_REQUIRED_FIELDS = ["student_no", "class_id", "student_name"]


@student_router.post("/students/extract", summary="自然语言提取学生信息", dependencies=[Depends(require_permission('student:create'))])
def extract_student(
    body: NLExtractRequest,
):
    logger.info("NL提取学生信息：text=%s", body.text[:80])
    result = extract_service.extract_fields(
        text=body.text,
        schema=StudentExtract,
        entity="student",
        required_fields=_STUDENT_REQUIRED_FIELDS,
    )
    if result["error"]:
        logger.warning("NL提取学生信息失败：%s", result["error"])
    else:
        logger.info("NL提取学生信息成功：提取字段=%s, 缺失=%s",
                    list(result["extracted"].keys()) if result["extracted"] else 0,
                    result["missing_required"])
    return success(result)


@student_router.post("/students/update/extract", summary="自然语言提取学生修改意图", dependencies=[Depends(require_permission('student:update'))])
def extract_student_update(
    body: NLExtractRequest,
    db: Session = Depends(get_db)
):
    logger.info("NL提取学生修改：text=%s", body.text[:80])
    result = extract_service.extract_fields(
        text=body.text,
        schema=StudentUpdateExtract,
        entity="student_update",
        required_fields=[],  # update 无必填限制
    )
    if result["extracted"]:
        ex = result["extracted"]
        sid = ex.get("student_id")
        sno = ex.get("student_no")

        # 解析定位：优先用 ID，否则通过学号查 ID
        if not sid and sno:
            student = get_by_student_no(sno, db)
            if student:
                ex["student_id"] = getattr(student, "id", None)
                ex["student_no"] = getattr(student, "student_no", None)
                ex["student_name"] = getattr(student, "student_name", None)
                logger.info("NL修改定位：学号 %s → 学生ID %s", sno, ex["student_id"])
            else:
                logger.warning("NL修改定位失败：学号 %s 对应的学生不存在", sno)
                result["error"] = f"学号 {sno} 对应的学生不存在"
                result["extracted"] = None

    if result["error"]:
        logger.warning("NL提取学生修改失败：%s", result["error"])
    else:
        ex = result.get("extracted", {})
        changes = ex.get("changes", {}) if ex else {}
        logger.info("NL提取学生修改成功：student_id=%s, 变更字段=%s",
                    ex.get("student_id") if ex else None,
                    list(changes.keys()) if changes else [])
    return success(result)


@student_router.post("/students", summary="创建学生", dependencies=[Depends(require_permission('student:create'))])
def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db)
):
    logger.info("创建学生：student_no=%s, name=%s", student_data.student_no, student_data.student_name)
    try:
        result = student_service.create_student(student_data, db)
        logger.info("创建学生成功：student_no=%s", student_data.student_no)
        return success(result, "创建成功")
    except ValueError as e:
        # 业务校验类错误（如学号重复），属于预期内异常，记 WARNING
        logger.warning("创建学生失败（业务校验）：%s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 未预料到的异常，记完整堆栈进 error.log，方便排查
        logger.exception("创建学生异常：%s", e)
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@student_router.get("/students", summary="查询所有学生信息", dependencies=[Depends(require_permission('student:view'))])
def get_all_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    logger.info("查询所有学生：skip=%s, limit=%s", skip, limit)
    students, page, page_size, total = student_service.get_all_students(skip, limit, db)
    return success_page(students, page, page_size, total)


@student_router.get("/students/{student_id}", summary="根据ID查询学生", dependencies=[Depends(require_permission('student:view'))])
def get_student_by_id(
    student_id: int = Path(..., ge=1, le=999999),
    db: Session = Depends(get_db)
):
    logger.info("按ID查询学生：student_id=%s", student_id)
    try:
        result = student_service.get_student_by_id(student_id, db)
        return success(result)
    except ValueError as e:
        logger.warning("按ID查询学生失败：student_id=%s, %s", student_id, e)
        raise HTTPException(status_code=404, detail=str(e))


@student_router.get("/students/no/{student_no}", summary="根据学号查询学生", dependencies=[Depends(require_permission('student:view'))])
def get_student_by_no(
    student_no: str,
    db: Session = Depends(get_db)
):
    logger.info("按学号查询学生：student_no=%s", student_no)
    try:
        result = student_service.get_student_by_no(student_no, db)
        return success(result)
    except ValueError as e:
        logger.warning("按学号查询学生失败：student_no=%s, %s", student_no, e)
        raise HTTPException(status_code=404, detail=str(e))


@student_router.get("/students/class/{class_id}", summary="根据班级查询", dependencies=[Depends(require_permission('student:view'))])
def get_students_by_class(
    class_id: int = Path(..., ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    logger.info("按班级查询学生：class_id=%s, skip=%s, limit=%s", class_id, skip, limit)
    result, page, page_size, total = student_service.get_students_by_class(
        class_id, skip, limit, db
    )
    return success_page(result, page, page_size, total)


@student_router.patch("/students/{student_id}",
                      summary="更新学生信息（只改提供的字段）", dependencies=[Depends(require_permission('student:update'))])
def update_student(
    update_data: StudentUpdate,
    student_id: int = Path(..., ge=1, le=999999),
    db: Session = Depends(get_db)
):
    logger.info("更新学生：student_id=%s", student_id)
    try:
        result = student_service.update_student(student_id, update_data, db)
        logger.info("更新学生成功：student_id=%s", student_id)
        return success(result, "更新成功")
    except ValueError as e:
        logger.warning("更新学生失败：student_id=%s, %s", student_id, e)
        raise HTTPException(status_code=400 if "没有提供" in str(e) else 404,
                            detail=str(e))


@student_router.delete("/students/{student_id}", summary="逻辑删除学生", dependencies=[Depends(require_permission('student:delete'))])
def delete_student(
    student_id: int = Path(..., ge=1, le=999999),
    db: Session = Depends(get_db)
):
    logger.info("逻辑删除学生：student_id=%s", student_id)
    try:
        student_service.soft_delete_student(student_id, db)
        logger.info("逻辑删除学生成功：student_id=%s", student_id)
        return success(None, "删除成功")
    except ValueError as e:
        logger.warning("逻辑删除学生失败：student_id=%s, %s", student_id, e)
        raise HTTPException(status_code=404, detail=str(e))


@student_router.post("/students/{student_id}/restore", summary="恢复已删除学生", dependencies=[Depends(require_permission('student:restore'))])
def restore_student(
    student_id: int = Path(..., ge=1, le=999999),
    db: Session = Depends(get_db)
):
    logger.info("恢复已删除学生：student_id=%s", student_id)
    try:
        student_service.restore_student(student_id, db)
        logger.info("恢复学生成功：student_id=%s", student_id)
        return success(None, "恢复成功")
    except ValueError as e:
        logger.warning("恢复学生失败：student_id=%s, %s", student_id, e)
        raise HTTPException(status_code=404, detail=str(e))
