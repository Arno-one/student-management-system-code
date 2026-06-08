"""
登录认证 / RBAC 相关的数据模型。
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description='登录账号')
    password: str = Field(..., min_length=1, max_length=128, description='登录密码')


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128, description='旧密码')
    new_password: str = Field(..., min_length=8, max_length=128, description='新密码')


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description='登录账号')
    password: str = Field(..., min_length=8, max_length=128, description='初始密码')
    real_name: str = Field(..., min_length=1, max_length=50, description='真实姓名')
    phone: Optional[str] = Field(None, max_length=20, description='手机号')
    email: Optional[EmailStr] = Field(None, description='邮箱')
    status: int = Field(default=1, description='状态 1-启用 0-禁用')
    must_change_password: int = Field(default=1, description='首次登录是否必须修改密码')
    role_ids: List[int] = Field(default_factory=list, description='角色ID列表')


class UserUpdateRequest(BaseModel):
    real_name: Optional[str] = Field(None, min_length=1, max_length=50, description='真实姓名')
    phone: Optional[str] = Field(None, max_length=20, description='手机号')
    email: Optional[EmailStr] = Field(None, description='邮箱')
    status: Optional[int] = Field(None, description='状态 1-启用 0-禁用')
    must_change_password: Optional[int] = Field(None, description='首次登录是否必须修改密码')


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128, description='新密码')
    must_change_password: int = Field(default=1, description='下次登录是否强制改密')


class AssignRolesRequest(BaseModel):
    role_ids: List[int] = Field(default_factory=list, description='角色ID列表')


class RoleCreateRequest(BaseModel):
    role_code: str = Field(..., min_length=2, max_length=50, description='角色编码')
    role_name: str = Field(..., min_length=1, max_length=50, description='角色名称')
    status: int = Field(default=1, description='状态 1-启用 0-禁用')
    remark: Optional[str] = Field(None, max_length=255, description='备注')


class RoleUpdateRequest(BaseModel):
    role_name: Optional[str] = Field(None, min_length=1, max_length=50, description='角色名称')
    status: Optional[int] = Field(None, description='状态 1-启用 0-禁用')
    remark: Optional[str] = Field(None, max_length=255, description='备注')


class AssignPermissionsRequest(BaseModel):
    permission_ids: List[int] = Field(default_factory=list, description='权限ID列表')


class PermissionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    permission_code: str
    permission_name: str
    permission_type: str
    module: str
    action: Optional[str] = None
    route_path: Optional[str] = None
    visible: int
    sort_no: int
    status: int
    description: Optional[str] = None


class RoleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_code: str
    role_name: str
    status: int
    remark: Optional[str] = None


class UserInfo(BaseModel):
    id: int
    username: str
    real_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    status: int
    must_change_password: int
    last_login_at: Optional[str] = None
    roles: List[RoleBrief] = []
    permissions: List[str] = []
    menus: List[PermissionInfo] = []


class LoginResponse(BaseModel):
    token: str
    token_type: str = 'bearer'
    expires_in: int
    user: UserInfo
