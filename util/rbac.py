"""
FastAPI 鉴权依赖：解析 Bearer Token，构造当前登录用户，并提供角色/权限校验。
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from DAO import auth_dao
from util.auth import AuthError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)



def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if not credentials or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='未登录或登录已过期')

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload['sub'])
    except (AuthError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = auth_dao.get_user_with_roles(user_id, db)
    if not user or user.is_deleted != 0 or user.status != 1:
        raise HTTPException(status_code=401, detail='账号已失效，请重新登录')

    role_codes = sorted([
        role.role_code for role in user.roles
        if role.is_deleted == 0 and role.status == 1
    ])
    permission_codes = set(auth_dao.get_permission_codes_by_user_id(user.id, db))

    return {
        'id': user.id,
        'username': user.username,
        'real_name': user.real_name,
        'role_codes': role_codes,
        'permission_codes': permission_codes,
    }



def ensure_permission(current_user: dict, permission_code: str):
    if permission_code not in current_user['permission_codes']:
        raise HTTPException(status_code=403, detail=f'缺少权限: {permission_code}')



def require_permission(permission_code: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        ensure_permission(current_user, permission_code)
        return current_user

    return dependency



def require_role(role_code: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        if role_code not in current_user['role_codes']:
            raise HTTPException(status_code=403, detail=f'缺少角色: {role_code}')
        return current_user

    return dependency
