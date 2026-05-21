from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ClassCreateSchema(BaseModel):
    """班级创建/更新请求模型"""
    class_code: str = Field(..., min_length=1, max_length=50, description="班级编号")
    class_name: str = Field(..., min_length=1, max_length=50, description="班级名称")
    start_time: datetime = Field(..., description="开班时间")

class ClassUpdateSchema(BaseModel):
    """班级更新请求模型（部分字段可选）"""
    class_code: Optional[str] = Field(None, min_length=1, max_length=50, description="班级编号")
    class_name: Optional[str] = Field(None, min_length=1, max_length=50, description="班级名称")
    start_time: Optional[datetime] = Field(None, description="开班时间")

class ClassInfo(BaseModel):
    """班级响应模型"""
    id: int = Field(..., description="班级ID")
    class_code: str = Field(..., description="班级编号")
    class_name: str = Field(..., description="班级名称")
    start_time: datetime = Field(..., description="开班时间")
    is_deleted: int = Field(..., description="删除标识")
    create_time: datetime = Field(..., description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True