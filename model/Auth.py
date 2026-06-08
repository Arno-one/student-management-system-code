from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class SysUser(Base):
    __tablename__ = 'sys_user'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment='用户ID')
    username = Column(String(50), nullable=False, unique=True, index=True, comment='登录账号')
    password_hash = Column(String(255), nullable=False, comment='密码哈希（PBKDF2-SHA256）')
    real_name = Column(String(50), nullable=False, comment='真实姓名')
    phone = Column(String(20), default=None, comment='手机号')
    email = Column(String(100), default=None, comment='邮箱')
    status = Column(Integer, nullable=False, default=1, comment='状态 1-启用 0-禁用')
    must_change_password = Column(Integer, nullable=False, default=0, comment='首次登录是否必须修改密码 1-是 0-否')
    last_login_at = Column(DateTime, default=None, comment='最后登录时间')
    pwd_updated_at = Column(DateTime, nullable=False, default=datetime.now, comment='最近修改密码时间')
    is_deleted = Column(Integer, nullable=False, default=0, comment='逻辑删除 0-未删 1-已删')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    user_roles = relationship('SysUserRole', back_populates='user', cascade='all, delete-orphan')
    roles = relationship('SysRole', secondary='sys_user_role', back_populates='users', viewonly=True)


class SysRole(Base):
    __tablename__ = 'sys_role'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment='角色ID')
    role_code = Column(String(50), nullable=False, unique=True, index=True, comment='角色编码')
    role_name = Column(String(50), nullable=False, comment='角色名称')
    status = Column(Integer, nullable=False, default=1, comment='状态 1-启用 0-禁用')
    is_deleted = Column(Integer, nullable=False, default=0, comment='逻辑删除 0-未删 1-已删')
    remark = Column(String(255), default=None, comment='备注')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    user_roles = relationship('SysUserRole', back_populates='role', cascade='all, delete-orphan')
    role_permissions = relationship('SysRolePermission', back_populates='role', cascade='all, delete-orphan')
    users = relationship('SysUser', secondary='sys_user_role', back_populates='roles', viewonly=True)
    permissions = relationship('SysPermission', secondary='sys_role_permission', back_populates='roles', viewonly=True)


class SysPermission(Base):
    __tablename__ = 'sys_permission'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment='权限ID')
    permission_code = Column(String(100), nullable=False, unique=True, index=True, comment='权限编码')
    permission_name = Column(String(100), nullable=False, comment='权限名称')
    permission_type = Column(String(20), nullable=False, comment='权限类型 menu/action')
    module = Column(String(50), nullable=False, index=True, comment='所属模块')
    action = Column(String(50), default=None, comment='动作')
    route_path = Column(String(100), default=None, comment='前端路由，仅 menu 类型有值')
    visible = Column(Integer, nullable=False, default=1, comment='菜单是否展示 1-展示 0-不展示')
    sort_no = Column(Integer, nullable=False, default=0, comment='排序号')
    status = Column(Integer, nullable=False, default=1, comment='状态 1-启用 0-禁用')
    description = Column(String(255), default=None, comment='权限说明')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    role_permissions = relationship('SysRolePermission', back_populates='permission', cascade='all, delete-orphan')
    roles = relationship('SysRole', secondary='sys_role_permission', back_populates='permissions', viewonly=True)


class SysUserRole(Base):
    __tablename__ = 'sys_user_role'

    user_id = Column(Integer, ForeignKey('sys_user.id', ondelete='CASCADE'), primary_key=True, comment='用户ID')
    role_id = Column(Integer, ForeignKey('sys_role.id', ondelete='CASCADE'), primary_key=True, comment='角色ID')
    create_time = Column(DateTime, default=datetime.now, nullable=False, comment='创建时间')

    user = relationship('SysUser', back_populates='user_roles')
    role = relationship('SysRole', back_populates='user_roles')


class SysRolePermission(Base):
    __tablename__ = 'sys_role_permission'

    role_id = Column(Integer, ForeignKey('sys_role.id', ondelete='CASCADE'), primary_key=True, comment='角色ID')
    permission_id = Column(Integer, ForeignKey('sys_permission.id', ondelete='CASCADE'), primary_key=True, comment='权限ID')
    create_time = Column(DateTime, default=datetime.now, nullable=False, comment='创建时间')

    role = relationship('SysRole', back_populates='role_permissions')
    permission = relationship('SysPermission', back_populates='role_permissions')
