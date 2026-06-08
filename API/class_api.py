"""
班级管理Controller层 — MVC中的Controller
只负责HTTP请求/响应处理，不包含业务逻辑
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from scheme.class_scheme import ClassCreateSchema as ccs
from scheme.response_scheme import success, success_page
from service import class_service
from util.log import get_logger
from util.rbac import get_current_user, ensure_permission, require_permission

# 本模块专用 logger，来源标记为 API.class_api
logger = get_logger(__name__)

class_router = APIRouter()


@class_router.post("/create_or_update_class", description='新增修改班级数据')
def create_or_update_class(
    class_data: ccs,
    id: int = None,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    # id 有值是修改，没值是新增，日志里区分一下方便排查
    ensure_permission(current_user, 'class:update' if id else 'class:create')
    logger.info("%s班级：id=%s", "修改" if id else "新增", id)
    try:
        result = class_service.create_or_update_class(class_data, db, id)
        logger.info("班级操作成功：id=%s", id)
        return success(result, "操作成功")
    except ValueError as e:
        logger.warning("班级新增/修改失败：id=%s, %s", id, e)
        raise HTTPException(status_code=404, detail=str(e))


@class_router.delete("/del_class", description='删除班级数据', dependencies=[Depends(require_permission('class:delete'))])
def del_class(id: int, db=Depends(get_db)):
    logger.info("删除班级：id=%s", id)
    result = class_service.delete_class(id, db)
    if result is None:
        logger.warning("删除班级失败：没有id为%s的数据", id)
        raise HTTPException(status_code=404, detail=f"没有id为{id}的数据可删除")
    logger.info("删除班级成功：id=%s, name=%s", id, result.class_name)
    return success(result, f"删除{result.class_name}成功")


@class_router.get(
    "/get_class",
    description='分页查询所有数据',
    dependencies=[Depends(require_permission('class:view'))]
)
def get_classes(
    db=Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=1, ge=1)
):
    logger.info("分页查询班级：page=%s, limit=%s", page, limit)
    info, p, size, total = class_service.get_classes(page, limit, db)
    return success_page(info, p, size, total)


@class_router.get("/get_class/{id}", description='根据id查询班级', dependencies=[Depends(require_permission('class:view'))])
def get_class(id: int, db=Depends(get_db)):
    logger.info("按id查询班级：id=%s", id)
    try:
        result = class_service.get_class_by_id(id, db)
        return success(result)
    except ValueError as e:
        logger.warning("按id查询班级失败：id=%s, %s", id, e)
        raise HTTPException(status_code=404, detail=str(e))
