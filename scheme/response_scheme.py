"""
统一API响应模型 — MVC中的View层
所有API接口统一使用此模块中定义的响应格式：{code, msg, data, total}

设计说明：
- 不管成功还是失败，前端拿到的结构都是一致的四个字段：
    code  ：业务/HTTP状态码，200 表示成功
    msg   ：提示信息（中文）
    data  ：真正的业务数据（对象、列表或 None）
    total ：数据总条数（列表场景下有意义；单条/无数据时为 None）
- 分页接口在四个字段基础上额外多带 page、page_size，方便前端做分页控件。
"""
from pydantic import BaseModel
from typing import Any, Optional, List, TypeVar, Generic


class APIResponse(BaseModel):
    """统一非分页响应格式：{code, msg, data, total}"""
    code: int = 200
    msg: str = "success"
    data: Optional[Any] = None
    total: Optional[int] = None

    class Config:
        from_attributes = True


T = TypeVar('T')


class PageResponse(BaseModel, Generic[T]):
    """统一分页响应格式：在 {code, msg, data, total} 基础上多带 page、page_size"""
    code: int = 200
    msg: str = "success"
    data: List[T]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


def success(data: Any = None, msg: str = "success", total: Optional[int] = None) -> dict:
    """
    构建成功响应，统一返回 {code, msg, data, total}。

    :param data: 业务数据（对象/列表/None）
    :param msg: 提示信息
    :param total: 总条数；不传时，如果 data 是列表则自动取 len(data)，否则为 None
    """
    # data 是列表又没显式传 total 时，自动用列表长度兜底，省得每个接口都手动算
    if total is None and isinstance(data, list):
        total = len(data)
    return {"code": 200, "msg": msg, "data": data, "total": total}


def success_page(data: list, page: int, page_size: int, total: int, msg: str = "success") -> dict:
    """
    构建分页成功响应：{code, msg, data, total, page, page_size}。

    :param data: 当前页的数据列表
    :param page: 当前页码
    :param page_size: 每页条数
    :param total: 总条数
    :param msg: 提示信息
    """
    return {
        "code": 200,
        "msg": msg,
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def error(code: int = 500, msg: str = "服务器内部错误", data: Any = None) -> dict:
    """构建错误响应，结构同样是 {code, msg, data, total}，便于前端统一处理"""
    return {"code": code, "msg": msg, "data": data, "total": None}
