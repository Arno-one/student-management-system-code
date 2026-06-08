from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from  DAO import student_dao,score_dao, talk_dao
from enum import Enum
from service import work_service
from util import email as email_util
from util.log import get_logger
from util.rbac import get_current_user, require_permission
from scheme.response_scheme import success  # 统一响应封装 {code, msg, data, total}
from pydantic import BaseModel

# 本模块专用 logger，来源标记为 API.work_api
logger = get_logger(__name__)

woker = APIRouter()
# 邮件模块单独用一个路由，方便在 docs 里独立成一个模块
email_router = APIRouter()


class CreateSessionBody(BaseModel):
    user_id: str
    title: str = "新对话"


class TalkBody(BaseModel):
    session_id: int
    user_id: str
    prompt: str

class style(str, Enum):
    humor = "幽默"
    serious = "严肃"
    incentive = "激励"
    criticism = "批判"

@woker.post("/evaluation", summary="评价风格：1.幽默,2.严肃,3.激励,4.批判", dependencies=[Depends(require_permission('work:use'))])
def evaluation(student_id: int,style: style,db: Session = Depends(get_db)):
    logger.info("生成学生评价：student_id=%s, style=%s", student_id, style.value)
    student = student_dao.get_by_id(student_id, db)
    stu_name= student.student_name
    sex = student.gender
    scores = score_dao.query_score(db, student_no=student.student_no)

    if not scores:
        # 没有成绩记录时，走统一的异常处理，返回 {code, msg, data, total}
        logger.warning("生成评价失败：学生 %s（id=%s）没有成绩记录", stu_name, student_id)
        raise HTTPException(status_code=404, detail=f"学生 {stu_name} 没有成绩记录")

    latest_score = scores[0]
    stu_score = latest_score.score
    result = work_service.evaluation_stu(stu_name, sex, stu_score, style)
    logger.info("生成学生评价成功：student_id=%s", student_id)
    return success(result, "评价生成成功")


@woker.post("/image", summary="文生图", dependencies=[Depends(require_permission('work:use'))])
def generate_image(prompt: str):
    """
        调用阿里云通义万相 qwen-image-2.0-pro 文生图接口
        :param prompt: 用户输入的提示词字符串
        :return: 接口返回的图片结果（包含图片URL）
    """
    logger.info("文生图：prompt=%s", prompt)
    result = work_service.generate_image(prompt)
    if result.get("success"):
        logger.info("文生图成功：prompt=%s", prompt[:50])
    else:
        logger.error("文生图失败：prompt=%s, error=%s", prompt[:50], result.get("error"))
    return success(result, "文生图成功")

# ==================== 多轮记忆对话（持久化版） ====================

@woker.get("/talks/sessions", summary="获取用户的所有历史会话", dependencies=[Depends(require_permission('work:use'))])
def list_sessions(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """返回当前登录用户所有未删除的会话列表，按更新时间倒序"""
    user_id = current_user['username']
    logger.info("获取会话列表：user_id=%s", user_id)
    sessions = talk_dao.get_sessions_by_user(user_id, db)
    return success([
        {
            "id": s.id,
            "user_id": s.user_id,
            "title": s.session_title,
            "summary": s.summary,
            "style": s.style,
            "create_time": s.create_time.strftime("%Y-%m-%d %H:%M:%S") if s.create_time else None,
            "update_time": s.update_time.strftime("%Y-%m-%d %H:%M:%S") if s.update_time else None,
        }
        for s in sessions
    ], "查询成功")


@woker.post("/talks/sessions", summary="创建新会话", dependencies=[Depends(require_permission('work:use'))])
def create_session(body: CreateSessionBody, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """为当前登录用户创建一个新的空白会话"""
    user_id = current_user['username']
    logger.info("创建会话：user_id=%s, title=%s", user_id, body.title)
    session = talk_dao.create_session(user_id, body.title, db)
    return success({
        "id": session.id,
        "user_id": session.user_id,
        "title": session.session_title,
        "create_time": session.create_time.strftime("%Y-%m-%d %H:%M:%S") if session.create_time else None,
    }, "会话已创建")


@woker.delete("/talks/sessions/{session_id}", summary="删除会话（逻辑删除）", dependencies=[Depends(require_permission('work:use'))])
def delete_session(session_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """逻辑删除指定会话"""
    user_id = current_user['username']
    logger.info("删除会话：session_id=%s, user_id=%s", session_id, user_id)
    session = talk_dao.get_session_by_id(session_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已删除")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作该会话")
    ok = talk_dao.soft_delete_session(session_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或已删除")
    return success(None, "会话已删除")


@woker.get("/talks/{session_id}/messages", summary="获取会话的全部历史消息", dependencies=[Depends(require_permission('work:use'))])
def get_messages(session_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """返回指定会话的全部消息（按时间正序），用于前端恢复对话界面"""
    logger.info("获取会话消息：session_id=%s", session_id)
    session = talk_dao.get_session_by_id(session_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已删除")
    if session.user_id != current_user['username']:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    messages = talk_dao.get_messages_by_session(session_id, db)
    return success([
        {
            "id": m.id,
            "role": m.role,
            "user_content": m.user_content,
            "ai_content": m.ai_content,
            "create_time": m.create_time.strftime("%Y-%m-%d %H:%M:%S") if m.create_time else None,
        }
        for m in messages
    ], "查询成功")


@woker.post("/talks", summary="多轮记忆对话（发送消息）", dependencies=[Depends(require_permission('work:use'))])
def talks(body: TalkBody, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    多轮记忆对话接口：从数据库加载历史上下文，调用大模型，持久化本轮对话
    """
    user_id = current_user['username']
    logger.info("多轮对话：user_id=%s, session_id=%s", user_id, body.session_id)
    reply = work_service.talks(body.session_id, user_id, body.prompt, db)
    if isinstance(reply, dict) and "error" in reply:
        logger.warning("多轮对话失败：user_id=%s, session_id=%s, error=%s", user_id, body.session_id, reply["error"])
        raise HTTPException(status_code=400, detail=reply["error"])
    logger.info("多轮对话成功：user_id=%s, session_id=%s, reply_len=%s", user_id, body.session_id, len(reply) if isinstance(reply, str) else 0)
    return success(reply, "对话成功")


@woker.post("/talks/clear", summary="清空指定会话的对话消息", dependencies=[Depends(require_permission('work:use'))])
def clear_talks(session_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    清空某个会话的全部历史消息（保留会话本身）
    """
    user_id = current_user['username']
    logger.info("清空对话消息：user_id=%s, session_id=%s", user_id, session_id)
    result = work_service.clear_talks(session_id, user_id, db)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return success(result, "消息已清空")


@woker.get("/weather", summary="天气查询（经纬度/行政区划编码 二选一）", dependencies=[Depends(require_permission('work:use'))])
def query_weather(location: str = None, adcode: str = None, weather_type: str = "now",
                  added_fields: str = None, get_md: int = None):
    """
    调用腾讯地图天气接口查询天气，location 和 adcode 二选一传入
    :param location: 经纬度坐标，格式"纬度,经度"，例如 39.905023,116.724502
    :param adcode: 行政区划编码，例如 130681
    :param weather_type: 天气类型，now=实时(默认) / future=多日预报 / hours=24小时逐时
    :param added_fields: 附加字段，多个用逗号分隔，例如 alarm,air
    :param get_md: 仅 future 生效，0=当日+未来3天(默认) / 1=当日+未来6天
    :return: 天气数据
    """
    logger.info("天气查询：location=%s, adcode=%s, type=%s", location, adcode, weather_type)
    result = work_service.query_weather(location, adcode, weather_type, added_fields, get_md)
    if "error" in result:
        logger.warning("天气查询失败：%s", result["error"])
    return success(result, "天气查询成功")


@woker.get("/geocoder", summary="经纬度查询（地址解析为经纬度）", dependencies=[Depends(require_permission('work:use'))])
def address_to_location(address: str, policy: int = 0):
    """
    调用腾讯地图地理编码接口，把文本地址解析成经纬度
    :param address: 待解析地址，标准模式(policy=0)必须带城市，例如 北京市海淀区彩和坊路海淀西大街74号
    :param policy: 解析策略，0=标准模式(默认) / 1=宽松模式(可省略城市)
        :return: 经纬度、结构化地址、行政区划编码等信息
    """
    logger.info("地址解析：address=%s, policy=%s", address, policy)
    result = work_service.address_to_location(address, policy)
    if "error" in result:
        logger.warning("地址解析失败：%s", result["error"])
    return success(result, "地址解析成功")


@email_router.post("/generate", summary="第一步：大模型生成邮件内容（不发送）", dependencies=[Depends(require_permission('email:send'))])
def generate_email(prompt: str):
    """
    一句话需求 -> 大模型自动生成邮件主题和正文，仅返回内容供用户编辑确认，不会发送。
    :param prompt: 邮件需求描述，例如"给老师写一封请假邮件，请假两天"
    :return: 生成的邮件内容 {subject: 主题, body: 正文}
    """
    logger.info("生成邮件内容：prompt=%s", prompt)
    result = email_util.generate_email_content(prompt)
    if result.get("success"):
        logger.info("邮件内容生成成功：prompt=%s", prompt[:50])
    else:
        logger.error("邮件内容生成失败：prompt=%s, error=%s", prompt[:50], result.get("error"))
    return success(result, "邮件内容已生成")


@email_router.post("/send", summary="第二步：发送用户确认后的邮件", dependencies=[Depends(require_permission('email:send'))])
def send_email(subject: str, body: str, receiver: str = "786453528@qq.com"):
    """
    把用户确认（可能已编辑修改）后的邮件主题、正文发送到目标邮箱。
    :param subject: 邮件主题
    :param body: 邮件正文
    :param receiver: 收件邮箱，默认 786453528@qq.com
    :return: 发送结果
    """
    logger.info("发送邮件：receiver=%s, subject=%s", receiver, subject)
    result = email_util.send_email(subject, body, receiver)
    # 发送失败时返回 success=False，前端据此提示
    if result.get("success"):
        logger.info("邮件发送成功：receiver=%s", receiver)
    else:
        # 发送失败属于异常情况，记 ERROR 进 error.log，方便排查 SMTP 问题
        logger.error("邮件发送失败：receiver=%s, %s", receiver, result.get("message"))
    return success(result, "邮件已发送" if result.get("success") else "邮件发送失败")
