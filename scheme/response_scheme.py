"""
统一API响应模型 — MVC中的View层
所有API接口统一使用此模块中定义的响应格式
"""
from pydantic import BaseModel
from typing import Any, Optional, List, TypeVar, Generic


class APIResponse(BaseModel):
    """统一非分页响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None

    class Config:
        from_attributes = True


T = TypeVar('T')


class PageResponse(BaseModel, Generic[T]):
    """统一分页响应格式"""
    code: int = 200
    message: str = "success"
    data: List[T]
    page: int
    page_size: int
    total: int

    class Config:
        from_attributes = True


def success(data: Any = None, message: str = "success") -> dict:
    """构建成功响应"""
    return {"code": 200, "message": message, "data": data}


def success_page(data: list, page: int, page_size: int, total: int, message: str = "success") -> dict:
    """构建分页成功响应"""
    return {
        "code": 200,
        "message": message,
        "data": data,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def error(code: int = 500, message: str = "服务器内部错误") -> dict:
    """构建错误响应（通常由HTTPException替代，此函数用于特殊场景）"""
    return {"code": code, "message": message, "data": None}