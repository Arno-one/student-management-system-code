"""
认证接口：登录、获取当前用户、修改密码。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from scheme.auth_scheme import LoginRequest, ChangePasswordRequest
from scheme.response_scheme import success
from service import auth_service
from util.auth import AuthError
from util.log import get_logger
from util.rbac import get_current_user

logger = get_logger(__name__)

auth_router = APIRouter()


@auth_router.post('/login', summary='账号登录')
def login(data: LoginRequest, db: Session = Depends(get_db)):
    logger.info('用户登录尝试：username=%s', data.username)
    try:
        result = auth_service.login(data.username, data.password, db)
        logger.info('用户登录成功：username=%s', data.username)
        return success(result, '登录成功')
    except AuthError as e:
        logger.warning('用户登录失败：username=%s, %s', data.username, e)
        raise HTTPException(status_code=401, detail=str(e))


@auth_router.get('/me', summary='获取当前登录用户')
def me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info('获取当前用户信息：user_id=%s', current_user['id'])
    try:
        result = auth_service.get_current_user_info(current_user['id'], db)
        return success(result, '查询成功')
    except AuthError as e:
        logger.warning('获取当前用户信息失败：user_id=%s, %s', current_user['id'], e)
        raise HTTPException(status_code=401, detail=str(e))


@auth_router.post('/change-password', summary='修改当前用户密码')
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info('用户修改密码：user_id=%s', current_user['id'])
    try:
        auth_service.change_password(current_user['id'], data.old_password, data.new_password, db)
        logger.info('用户修改密码成功：user_id=%s', current_user['id'])
        return success(None, '密码修改成功')
    except AuthError as e:
        logger.warning('用户修改密码失败：user_id=%s, %s', current_user['id'], e)
        raise HTTPException(status_code=400 if '原密码' in str(e) or '新密码' in str(e) or '长度' in str(e) or '必须' in str(e) else 401,
                            detail=str(e))
