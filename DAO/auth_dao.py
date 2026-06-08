"""
RBAC / 登录认证 相关 DAO。
只负责数据库读写，不包含业务规则。
"""
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from model.Auth import SysUser, SysRole, SysPermission, SysUserRole, SysRolePermission
from util.log import get_logger

logger = get_logger(__name__)


# ==================== 用户 ====================
def get_user_by_id(user_id: int, db: Session):
    return db.query(SysUser).filter(
        SysUser.id == user_id,
        SysUser.is_deleted == 0
    ).first()


def get_user_by_username(username: str, db: Session):
    return db.query(SysUser).filter(
        SysUser.username == username,
        SysUser.is_deleted == 0
    ).first()


def get_user_with_roles(user_id: int, db: Session):
    return db.query(SysUser).options(
        joinedload(SysUser.roles)
    ).filter(
        SysUser.id == user_id,
        SysUser.is_deleted == 0
    ).first()


def get_user_with_roles_by_username(username: str, db: Session):
    return db.query(SysUser).options(
        joinedload(SysUser.roles)
    ).filter(
        SysUser.username == username,
        SysUser.is_deleted == 0
    ).first()


def list_users(db: Session, skip: int = 0, limit: int = 100, username: str = None, real_name: str = None, status: int = None):
    query = db.query(SysUser).filter(SysUser.is_deleted == 0)
    if username:
        query = query.filter(SysUser.username.like(f"%{username}%"))
    if real_name:
        query = query.filter(SysUser.real_name.like(f"%{real_name}%"))
    if status is not None:
        query = query.filter(SysUser.status == status)
    total = query.count()
    records = query.order_by(SysUser.id.asc()).offset(skip).limit(limit).all()
    return records, total


def create_user(data: dict, db: Session):
    user = SysUser(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("系统用户已创建：id=%s, username=%s", user.id, user.username)
    return user


def update_user(user_id: int, update_data: dict, db: Session):
    user = get_user_by_id(user_id, db)
    if not user:
        return None
    forbidden = {'id', 'username', 'create_time'}
    for key, value in update_data.items():
        if key not in forbidden and hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    logger.info("系统用户已更新：id=%s, fields=%s", user_id, list(update_data.keys()))
    return user


def update_user_password(user_id: int, password_hash: str, must_change_password: int, db: Session):
    user = get_user_by_id(user_id, db)
    if not user:
        return None
    user.password_hash = password_hash
    user.must_change_password = must_change_password
    user.pwd_updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    logger.info("系统用户密码已更新：id=%s", user_id)
    return user


def update_last_login(user_id: int, db: Session):
    user = get_user_by_id(user_id, db)
    if not user:
        return None
    user.last_login_at = datetime.now()
    db.commit()
    return user


def replace_user_roles(user_id: int, role_ids: list[int], db: Session):
    db.query(SysUserRole).filter(SysUserRole.user_id == user_id).delete()
    if role_ids:
        db.add_all([SysUserRole(user_id=user_id, role_id=role_id) for role_id in role_ids])
    db.commit()
    logger.info("用户角色已重置：user_id=%s, role_ids=%s", user_id, role_ids)


# ==================== 角色 ====================
def get_role_by_id(role_id: int, db: Session):
    return db.query(SysRole).filter(
        SysRole.id == role_id,
        SysRole.is_deleted == 0
    ).first()


def get_role_by_code(role_code: str, db: Session):
    return db.query(SysRole).filter(
        SysRole.role_code == role_code,
        SysRole.is_deleted == 0
    ).first()


def get_role_with_permissions(role_id: int, db: Session):
    return db.query(SysRole).options(
        joinedload(SysRole.permissions)
    ).filter(
        SysRole.id == role_id,
        SysRole.is_deleted == 0
    ).first()


def list_roles(db: Session, skip: int = 0, limit: int = 100, role_name: str = None, status: int = None):
    query = db.query(SysRole).filter(SysRole.is_deleted == 0)
    if role_name:
        query = query.filter(SysRole.role_name.like(f"%{role_name}%"))
    if status is not None:
        query = query.filter(SysRole.status == status)
    total = query.count()
    records = query.order_by(SysRole.id.asc()).offset(skip).limit(limit).all()
    return records, total


def create_role(data: dict, db: Session):
    role = SysRole(**data)
    db.add(role)
    db.commit()
    db.refresh(role)
    logger.info("系统角色已创建：id=%s, role_code=%s", role.id, role.role_code)
    return role


def update_role(role_id: int, update_data: dict, db: Session):
    role = get_role_by_id(role_id, db)
    if not role:
        return None
    forbidden = {'id', 'role_code', 'create_time'}
    for key, value in update_data.items():
        if key not in forbidden and hasattr(role, key):
            setattr(role, key, value)
    db.commit()
    db.refresh(role)
    logger.info("系统角色已更新：id=%s, fields=%s", role_id, list(update_data.keys()))
    return role


def replace_role_permissions(role_id: int, permission_ids: list[int], db: Session):
    db.query(SysRolePermission).filter(SysRolePermission.role_id == role_id).delete()
    if permission_ids:
        db.add_all([SysRolePermission(role_id=role_id, permission_id=permission_id) for permission_id in permission_ids])
    db.commit()
    logger.info("角色权限已重置：role_id=%s, permission_ids=%s", role_id, permission_ids)


# ==================== 权限 ====================
def list_permissions(db: Session, module: str = None, permission_type: str = None, only_enabled: bool = True):
    query = db.query(SysPermission)
    if only_enabled:
        query = query.filter(SysPermission.status == 1)
    if module:
        query = query.filter(SysPermission.module == module)
    if permission_type:
        query = query.filter(SysPermission.permission_type == permission_type)
    return query.order_by(SysPermission.sort_no.asc(), SysPermission.id.asc()).all()


def get_permissions_by_codes(permission_codes: list[str], db: Session):
    if not permission_codes:
        return []
    return db.query(SysPermission).filter(SysPermission.permission_code.in_(permission_codes)).all()


def get_roles_by_ids(role_ids: list[int], db: Session):
    if not role_ids:
        return []
    return db.query(SysRole).filter(
        SysRole.id.in_(role_ids),
        SysRole.is_deleted == 0,
        SysRole.status == 1
    ).all()


def get_permissions_by_ids(permission_ids: list[int], db: Session):
    if not permission_ids:
        return []
    return db.query(SysPermission).filter(
        SysPermission.id.in_(permission_ids),
        SysPermission.status == 1
    ).all()


def get_permission_codes_by_user_id(user_id: int, db: Session):
    rows = (
        db.query(SysPermission.permission_code)
        .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
        .join(SysRole, SysRole.id == SysRolePermission.role_id)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .join(SysUser, SysUser.id == SysUserRole.user_id)
        .filter(
            SysUser.id == user_id,
            SysUser.is_deleted == 0,
            SysUser.status == 1,
            SysRole.is_deleted == 0,
            SysRole.status == 1,
            SysPermission.status == 1,
        )
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


def get_menu_permissions_by_user_id(user_id: int, db: Session):
    return (
        db.query(SysPermission)
        .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
        .join(SysRole, SysRole.id == SysRolePermission.role_id)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .join(SysUser, SysUser.id == SysUserRole.user_id)
        .filter(
            SysUser.id == user_id,
            SysUser.is_deleted == 0,
            SysUser.status == 1,
            SysRole.is_deleted == 0,
            SysRole.status == 1,
            SysPermission.status == 1,
            SysPermission.permission_type == 'menu',
        )
        .distinct()
        .order_by(SysPermission.sort_no.asc(), SysPermission.id.asc())
        .all()
    )
