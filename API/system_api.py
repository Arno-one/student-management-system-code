"""
系统管理接口：用户管理、角色管理、权限查询。
说明：整个路由仅允许 admin 角色访问。
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from database import get_db
from scheme.auth_scheme import (
    UserCreateRequest,
    UserUpdateRequest,
    ResetPasswordRequest,
    AssignRolesRequest,
    RoleCreateRequest,
    RoleUpdateRequest,
    AssignPermissionsRequest,
)
from scheme.response_scheme import success, success_page
from service import auth_service
from util.auth import AuthError
from util.log import get_logger
from util.rbac import require_permission, require_role

logger = get_logger(__name__)

system_router = APIRouter(dependencies=[Depends(require_role('admin'))])


@system_router.get('/users', summary='分页查询系统用户', dependencies=[Depends(require_permission('system:user:view'))])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    username: str | None = Query(None),
    real_name: str | None = Query(None),
    status: int | None = Query(None, ge=0, le=1),
    db: Session = Depends(get_db),
):
    logger.info('分页查询系统用户：skip=%s, limit=%s, username=%s, real_name=%s, status=%s', skip, limit, username, real_name, status)
    items, page, page_size, total = auth_service.list_users(skip, limit, username, real_name, status, db)
    return success_page(items, page, page_size, total)


@system_router.post('/users', summary='创建系统用户', dependencies=[Depends(require_permission('system:user:create'))])
def create_user(data: UserCreateRequest, db: Session = Depends(get_db)):
    logger.info('创建系统用户：username=%s', data.username)
    try:
        result = auth_service.create_user(data, db)
        logger.info('创建系统用户成功：username=%s', data.username)
        return success({
            'id': result.id,
            'username': result.username,
            'real_name': result.real_name,
        }, '创建成功')
    except AuthError as e:
        logger.warning('创建系统用户失败：username=%s, %s', data.username, e)
        raise HTTPException(status_code=409 if '已存在' in str(e) else 400, detail=str(e))


@system_router.patch('/users/{user_id}', summary='更新系统用户', dependencies=[Depends(require_permission('system:user:update'))])
def update_user(
    data: UserUpdateRequest,
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    logger.info('更新系统用户：user_id=%s', user_id)
    try:
        result = auth_service.update_user(user_id, data, db)
        logger.info('更新系统用户成功：user_id=%s', user_id)
        return success({
            'id': result.id,
            'username': result.username,
            'real_name': result.real_name,
        }, '更新成功')
    except AuthError as e:
        logger.warning('更新系统用户失败：user_id=%s, %s', user_id, e)
        raise HTTPException(status_code=404 if '不存在' in str(e) else 400, detail=str(e))


@system_router.post('/users/{user_id}/reset-password', summary='重置用户密码', dependencies=[Depends(require_permission('system:user:reset-password'))])
def reset_password(
    data: ResetPasswordRequest,
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    logger.info('重置用户密码：user_id=%s', user_id)
    try:
        auth_service.reset_password(user_id, data.new_password, data.must_change_password, db)
        logger.info('重置用户密码成功：user_id=%s', user_id)
        return success(None, '密码重置成功')
    except AuthError as e:
        logger.warning('重置用户密码失败：user_id=%s, %s', user_id, e)
        raise HTTPException(status_code=404 if '不存在' in str(e) else 400, detail=str(e))


@system_router.post('/users/{user_id}/assign-roles', summary='为用户分配角色', dependencies=[Depends(require_permission('system:user:assign-roles'))])
def assign_roles(
    data: AssignRolesRequest,
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    logger.info('分配用户角色：user_id=%s, role_ids=%s', user_id, data.role_ids)
    try:
        result = auth_service.assign_roles(user_id, data.role_ids, db)
        logger.info('分配用户角色成功：user_id=%s', user_id)
        return success({
            'id': result.id,
            'username': result.username,
            'role_ids': [role.id for role in result.roles],
        }, '角色分配成功')
    except AuthError as e:
        logger.warning('分配用户角色失败：user_id=%s, %s', user_id, e)
        raise HTTPException(status_code=404 if '不存在' in str(e) else 400, detail=str(e))


@system_router.get('/roles', summary='分页查询系统角色', dependencies=[Depends(require_permission('system:role:view'))])
def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role_name: str | None = Query(None),
    status: int | None = Query(None, ge=0, le=1),
    db: Session = Depends(get_db),
):
    logger.info('分页查询系统角色：skip=%s, limit=%s, role_name=%s, status=%s', skip, limit, role_name, status)
    items, page, page_size, total = auth_service.list_roles(skip, limit, role_name, status, db)
    return success_page(items, page, page_size, total)


@system_router.post('/roles', summary='创建系统角色', dependencies=[Depends(require_permission('system:role:create'))])
def create_role(data: RoleCreateRequest, db: Session = Depends(get_db)):
    logger.info('创建系统角色：role_code=%s', data.role_code)
    try:
        result = auth_service.create_role(data, db)
        logger.info('创建系统角色成功：role_code=%s', data.role_code)
        return success({
            'id': result.id,
            'role_code': result.role_code,
            'role_name': result.role_name,
        }, '创建成功')
    except AuthError as e:
        logger.warning('创建系统角色失败：role_code=%s, %s', data.role_code, e)
        raise HTTPException(status_code=409 if '已存在' in str(e) else 400, detail=str(e))


@system_router.patch('/roles/{role_id}', summary='更新系统角色', dependencies=[Depends(require_permission('system:role:update'))])
def update_role(
    data: RoleUpdateRequest,
    role_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    logger.info('更新系统角色：role_id=%s', role_id)
    try:
        result = auth_service.update_role(role_id, data, db)
        logger.info('更新系统角色成功：role_id=%s', role_id)
        return success({
            'id': result.id,
            'role_code': result.role_code,
            'role_name': result.role_name,
        }, '更新成功')
    except AuthError as e:
        logger.warning('更新系统角色失败：role_id=%s, %s', role_id, e)
        raise HTTPException(status_code=404 if '不存在' in str(e) else 400, detail=str(e))


@system_router.post('/roles/{role_id}/assign-permissions', summary='为角色分配权限', dependencies=[Depends(require_permission('system:role:assign-permissions'))])
def assign_permissions(
    data: AssignPermissionsRequest,
    role_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    logger.info('分配角色权限：role_id=%s, permission_ids=%s', role_id, data.permission_ids)
    try:
        result = auth_service.assign_permissions(role_id, data.permission_ids, db)
        logger.info('分配角色权限成功：role_id=%s', role_id)
        return success({
            'id': result.id,
            'role_code': result.role_code,
            'permission_ids': [item.id for item in result.permissions],
        }, '权限分配成功')
    except AuthError as e:
        logger.warning('分配角色权限失败：role_id=%s, %s', role_id, e)
        raise HTTPException(status_code=404 if '不存在' in str(e) else 400, detail=str(e))


@system_router.get('/permissions', summary='查询权限目录', dependencies=[Depends(require_permission('system:role:view'))])
def list_permissions(
    module: str | None = Query(None),
    permission_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    logger.info('查询权限目录：module=%s, permission_type=%s', module, permission_type)
    result = auth_service.list_permissions(module, permission_type, db)
    return success(result, '查询成功')
