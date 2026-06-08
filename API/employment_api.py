"""
就业管理Controller层 — MVC中的Controller
只负责HTTP请求/响应处理，不包含业务逻辑
"""
from fastapi import Depends, HTTPException, APIRouter, Query
from sqlalchemy.orm import Session
from database import get_db
from scheme import employment_scheme as EMP
from scheme.response_scheme import success, success_page
from service import employment_service
from util.log import get_logger
from util.rbac import require_permission

# 本模块专用 logger，来源标记为 API.employment_api
logger = get_logger(__name__)

employment_router = APIRouter()


@employment_router.post("/employment_create",
                        summary="新建学生就业信息", dependencies=[Depends(require_permission('employment:create'))])
def employment_create(
    data: EMP.EmploymentCreate,
    db: Session = Depends(get_db)
):
    logger.info("新建就业信息")
    try:
        result = employment_service.create_employment(data, db)
        logger.info("新建就业信息成功")
        return success(result, "创建成功")
    except ValueError as e:
        logger.warning("新建就业信息失败：%s", e)
        raise HTTPException(status_code=409, detail=str(e))


@employment_router.get("/employment_get/{emp_id}",
                       summary="根据id查询", dependencies=[Depends(require_permission('employment:view'))])
def employment_get(emp_id: int, db: Session = Depends(get_db)):
    logger.info("按id查询就业信息：emp_id=%s", emp_id)
    try:
        result = employment_service.get_employment_by_id(emp_id, db)
        return success(result)
    except ValueError as e:
        logger.warning("按id查询就业信息失败：emp_id=%s, %s", emp_id, e)
        raise HTTPException(status_code=404, detail=str(e))


@employment_router.get("/employment_list", summary="分页查询", dependencies=[Depends(require_permission('employment:view'))])
def get_employment_list(
    page: int = Query(1, ge=1),
    size: int = Query(10, le=100, ge=1),
    student_name: str = None,
    class_id: int = None,
    company_name: str = None,
    db: Session = Depends(get_db)
):
    logger.info("分页查询就业信息：page=%s, size=%s, student_name=%s, class_id=%s, company_name=%s",
                page, size, student_name, class_id, company_name)
    result = employment_service.get_employment_list(
        db, page, size, student_name, class_id, company_name
    )
    return success_page(
        result["list"], result["page"], result["size"], result["total"]
    )


@employment_router.put("/employment_update/{emp_id}",
                       summary="修改就业信息", dependencies=[Depends(require_permission('employment:update'))])
def employment_update(
    emp_id: int,
    data: EMP.EmploymentUpdate,
    db: Session = Depends(get_db)
):
    logger.info("修改就业信息：emp_id=%s", emp_id)
    try:
        result = employment_service.update_employment(emp_id, data, db)
        logger.info("修改就业信息成功：emp_id=%s", emp_id)
        return success(result, "更新成功")
    except ValueError as e:
        logger.warning("修改就业信息失败：emp_id=%s, %s", emp_id, e)
        raise HTTPException(status_code=404 if "不存在" in str(e) else 409,
                            detail=str(e))


@employment_router.delete("/employment_delete/{emp_id}", summary="逻辑删除", dependencies=[Depends(require_permission('employment:delete'))])
def employment_delete(emp_id: int, db: Session = Depends(get_db)):
    logger.info("逻辑删除就业信息：emp_id=%s", emp_id)
    try:
        result = employment_service.soft_delete_employment(emp_id, db)
        logger.info("逻辑删除就业信息成功：emp_id=%s", emp_id)
        return success(result, "删除成功")
    except ValueError as e:
        logger.warning("逻辑删除就业信息失败：emp_id=%s, %s", emp_id, e)
        raise HTTPException(status_code=404, detail=str(e))


@employment_router.put("/employment_recover/{emp_id}", summary="逻辑恢复", dependencies=[Depends(require_permission('employment:update'))])
def employment_recover(emp_id: int, db: Session = Depends(get_db)):
    logger.info("逻辑恢复就业信息：emp_id=%s", emp_id)
    try:
        result = employment_service.recover_employment(emp_id, db)
        logger.info("逻辑恢复就业信息成功：emp_id=%s", emp_id)
        return success(result, "恢复成功")
    except ValueError as e:
        logger.warning("逻辑恢复就业信息失败：emp_id=%s, %s", emp_id, e)
        raise HTTPException(status_code=404 if "不存在" in str(e) else 409,
                            detail=str(e))


@employment_router.delete("/employment_hard/{emp_id}", summary="物理删除", dependencies=[Depends(require_permission('employment:delete'))])
def employment_hard(emp_id: int, db: Session = Depends(get_db)):
    # 物理删除不可恢复，用 warning 级别留个醒目记录
    logger.warning("物理删除就业信息（不可恢复）：emp_id=%s", emp_id)
    try:
        result = employment_service.hard_delete_employment(emp_id, db)
        logger.info("物理删除就业信息成功：emp_id=%s", emp_id)
        return success(result, "删除成功")
    except ValueError as e:
        logger.warning("物理删除就业信息失败：emp_id=%s, %s", emp_id, e)
        raise HTTPException(status_code=404, detail=str(e))
