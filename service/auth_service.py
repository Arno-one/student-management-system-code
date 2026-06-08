"""
登录认证 / RBAC 业务逻辑层。
负责：登录、当前用户信息、修改密码、用户管理、角色管理、权限查询。
"""
import re
from sqlalchemy.orm import Session
from DAO import auth_dao
from util.auth import (
    AuthError,
    create_access_token,
    hash_password,
    verify_password,
    validate_password_strength,
)
from config import AUTH_TOKEN_EXPIRE_MINUTES
from util.log import get_logger

logger = get_logger(__name__)

ROLE_CODE_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_:-]{1,49}$')


def _format_dt(value):
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else None


def _serialize_role(role):
    return {
        'id': role.id,
        'role_code': role.role_code,
        'role_name': role.role_name,
        'status': role.status,
        'remark': role.remark,
    }


def _serialize_permission(permission):
    return {
        'id': permission.id,
        'permission_code': permission.permission_code,
        'permission_name': permission.permission_name,
        'permission_type': permission.permission_type,
        'module': permission.module,
        'action': permission.action,
        'route_path': permission.route_path,
        'visible': permission.visible,
        'sort_no': permission.sort_no,
        'status': permission.status,
        'description': permission.description,
    }


def build_user_info(user_id: int, db: Session):
    user = auth_dao.get_user_with_roles(user_id, db)
    if not user:
        raise AuthError('用户不存在')

    permission_codes = auth_dao.get_permission_codes_by_user_id(user_id, db)
    menus = auth_dao.get_menu_permissions_by_user_id(user_id, db)

    return {
        'id': user.id,
        'username': user.username,
        'real_name': user.real_name,
        'phone': user.phone,
        'email': user.email,
        'status': user.status,
        'must_change_password': user.must_change_password,
        'last_login_at': _format_dt(user.last_login_at),
        'roles': [_serialize_role(role) for role in sorted(user.roles, key=lambda x: x.id)],
        'permissions': sorted(permission_codes),
        'menus': [_serialize_permission(item) for item in menus],
    }


def login(username: str, password: str, db: Session):
    user = auth_dao.get_user_with_roles_by_username(username, db)
    if not user:
        logger.warning('登录失败：账号不存在 username=%s', username)
        raise AuthError('用户名或密码错误')
    if user.status != 1 or user.is_deleted != 0:
        logger.warning('登录失败：账号已禁用 username=%s', username)
        raise AuthError('账号已禁用，请联系管理员')
    if not verify_password(password, user.password_hash):
        logger.warning('登录失败：密码错误 username=%s', username)
        raise AuthError('用户名或密码错误')

    auth_dao.update_last_login(user.id, db)
    token = create_access_token(user.id, user.username)
    logger.info('登录成功：user_id=%s, username=%s', user.id, user.username)
    return {
        'token': token,
        'token_type': 'bearer',
        'expires_in': AUTH_TOKEN_EXPIRE_MINUTES * 60,
        'user': build_user_info(user.id, db),
    }


def get_current_user_info(user_id: int, db: Session):
    return build_user_info(user_id, db)


def change_password(user_id: int, old_password: str, new_password: str, db: Session):
    user = auth_dao.get_user_by_id(user_id, db)
    if not user:
        raise AuthError('用户不存在')
    if not verify_password(old_password, user.password_hash):
        raise AuthError('原密码不正确')
    if old_password == new_password:
        raise AuthError('新密码不能与旧密码相同')

    validate_password_strength(new_password)
    password_hash = hash_password(new_password)
    auth_dao.update_user_password(user_id, password_hash, 0, db)
    logger.info('用户修改密码成功：user_id=%s', user_id)
    return True


def _validate_status(value, field_name='状态'):
    if value is None:
        return
    if value not in (0, 1):
        raise AuthError(f'{field_name}只能是 0 或 1')


def _ensure_roles_exist(role_ids: list[int], db: Session):
    roles = auth_dao.get_roles_by_ids(role_ids, db)
    found_ids = {item.id for item in roles}
    missing = [role_id for role_id in role_ids if role_id not in found_ids]
    if missing:
        raise AuthError(f'角色不存在或不可用: {missing}')
    return roles


def _ensure_permissions_exist(permission_ids: list[int], db: Session):
    permissions = auth_dao.get_permissions_by_ids(permission_ids, db)
    found_ids = {item.id for item in permissions}
    missing = [permission_id for permission_id in permission_ids if permission_id not in found_ids]
    if missing:
        raise AuthError(f'权限不存在或不可用: {missing}')
    return permissions


def list_users(skip: int, limit: int, username: str, real_name: str, status: int | None, db: Session):
    records, total = auth_dao.list_users(db, skip, limit, username, real_name, status)
    items = []
    for user in records:
        user_full = auth_dao.get_user_with_roles(user.id, db)
        items.append({
            'id': user_full.id,
            'username': user_full.username,
            'real_name': user_full.real_name,
            'phone': user_full.phone,
            'email': user_full.email,
            'status': user_full.status,
            'must_change_password': user_full.must_change_password,
            'last_login_at': _format_dt(user_full.last_login_at),
            'create_time': _format_dt(user_full.create_time),
            'update_time': _format_dt(user_full.update_time),
            'role_ids': [role.id for role in sorted(user_full.roles, key=lambda x: x.id)],
            'roles': [_serialize_role(role) for role in sorted(user_full.roles, key=lambda x: x.id)],
        })
    page = skip // limit + 1 if limit > 0 else 1
    return items, page, limit, total


def create_user(data, db: Session):
    if auth_dao.get_user_by_username(data.username, db):
        raise AuthError(f'登录账号 {data.username} 已存在')
    _validate_status(data.status)
    _validate_status(data.must_change_password, '首次改密标记')
    _ensure_roles_exist(data.role_ids, db)

    create_data = {
        'username': data.username,
        'password_hash': hash_password(data.password),
        'real_name': data.real_name,
        'phone': data.phone,
        'email': data.email,
        'status': data.status,
        'must_change_password': data.must_change_password,
        'is_deleted': 0,
    }
    user = auth_dao.create_user(create_data, db)
    auth_dao.replace_user_roles(user.id, data.role_ids, db)
    return auth_dao.get_user_with_roles(user.id, db)


def update_user(user_id: int, data, db: Session):
    user = auth_dao.get_user_by_id(user_id, db)
    if not user:
        raise AuthError('用户不存在')
    _validate_status(data.status)
    _validate_status(data.must_change_password, '首次改密标记')

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise AuthError('没有提供要更新的字段')
    updated = auth_dao.update_user(user_id, update_data, db)
    return auth_dao.get_user_with_roles(updated.id, db)


def reset_password(user_id: int, new_password: str, must_change_password: int, db: Session):
    user = auth_dao.get_user_by_id(user_id, db)
    if not user:
        raise AuthError('用户不存在')
    _validate_status(must_change_password, '首次改密标记')
    validate_password_strength(new_password)
    auth_dao.update_user_password(user_id, hash_password(new_password), must_change_password, db)
    return True


def assign_roles(user_id: int, role_ids: list[int], db: Session):
    user = auth_dao.get_user_by_id(user_id, db)
    if not user:
        raise AuthError('用户不存在')
    _ensure_roles_exist(role_ids, db)
    auth_dao.replace_user_roles(user_id, role_ids, db)
    return auth_dao.get_user_with_roles(user_id, db)


def list_roles(skip: int, limit: int, role_name: str, status: int | None, db: Session):
    records, total = auth_dao.list_roles(db, skip, limit, role_name, status)
    items = []
    for role in records:
        role_full = auth_dao.get_role_with_permissions(role.id, db)
        permissions = sorted(role_full.permissions, key=lambda x: (x.sort_no, x.id))
        items.append({
            'id': role_full.id,
            'role_code': role_full.role_code,
            'role_name': role_full.role_name,
            'status': role_full.status,
            'remark': role_full.remark,
            'create_time': _format_dt(role_full.create_time),
            'update_time': _format_dt(role_full.update_time),
            'permission_ids': [item.id for item in permissions],
            'permission_codes': [item.permission_code for item in permissions],
            'permissions': [_serialize_permission(item) for item in permissions],
        })
    page = skip // limit + 1 if limit > 0 else 1
    return items, page, limit, total


def create_role(data, db: Session):
    if not ROLE_CODE_RE.match(data.role_code):
        raise AuthError('角色编码格式不正确：需以字母开头，只能包含字母、数字、下划线、冒号、短横线')
    if auth_dao.get_role_by_code(data.role_code, db):
        raise AuthError(f'角色编码 {data.role_code} 已存在')
    _validate_status(data.status)

    create_data = {
        'role_code': data.role_code,
        'role_name': data.role_name,
        'status': data.status,
        'remark': data.remark,
        'is_deleted': 0,
    }
    return auth_dao.create_role(create_data, db)


def update_role(role_id: int, data, db: Session):
    role = auth_dao.get_role_by_id(role_id, db)
    if not role:
        raise AuthError('角色不存在')
    _validate_status(data.status)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise AuthError('没有提供要更新的字段')
    return auth_dao.update_role(role_id, update_data, db)


def assign_permissions(role_id: int, permission_ids: list[int], db: Session):
    role = auth_dao.get_role_by_id(role_id, db)
    if not role:
        raise AuthError('角色不存在')
    _ensure_permissions_exist(permission_ids, db)
    auth_dao.replace_role_permissions(role_id, permission_ids, db)
    return auth_dao.get_role_with_permissions(role_id, db)


def list_permissions(module: str, permission_type: str, db: Session):
    permissions = auth_dao.list_permissions(db, module, permission_type, only_enabled=True)
    return [_serialize_permission(item) for item in permissions]
