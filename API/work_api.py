from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from  DAO import student_dao,score_dao
from enum import Enum
from service import work_service
from util import email as email_util
from util.log import get_logger
from scheme.response_scheme import success  # 统一响应封装 {code, msg, data, total}

# 本模块专用 logger，来源标记为 API.work_api
logger = get_logger(__name__)

woker = APIRouter()
# 邮件模块单独用一个路由，方便在 docs 里独立成一个模块
email_router = APIRouter()

class style(str, Enum):
    humor = "幽默"
    serious = "严肃"
    incentive = "激励"
    criticism = "批判"

@woker.post("/evaluation", summary="评价风格：1.幽默,2.严肃,3.激励,4.批判")
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


@woker.post("/image", summary="文生图")
def generate_image(prompt: str):
    """
        调用阿里云通义万相 qwen-image-2.0-pro 文生图接口
        :param prompt: 用户输入的提示词字符串
        :return: 接口返回的图片结果（包含图片URL）
    """
    logger.info("文生图：prompt=%s", prompt)
    return success(work_service.generate_image(prompt), "文生图成功")

@woker.post("/talks", summary="多轮记忆对话")
def talks(session_id: str, prompt: str):
    """
    多轮记忆对话接口：同一个 session_id 下的多次请求会带上历史上下文，实现连续对话
    :param session_id: 会话标识，前端自己生成（比如用户ID或一个唯一串），同一会话保持不变
    :param prompt: 用户这一轮输入的内容
    :return: 大模型这一轮的回复
    """
    logger.info("多轮对话：session_id=%s", session_id)
    reply = work_service.talks(session_id, prompt)
    # data 直接放回复正文，前端只展示对话内容，不必再解析嵌套的 reply 字段
    return success(reply, "对话成功")


@woker.post("/talks/clear", summary="清空指定会话的对话记忆")
def clear_talks(session_id: str):
    """
    清空某个会话的历史记忆，下次对话就是全新开始
    :param session_id: 要清空的会话标识
    """
    logger.info("清空对话记忆：session_id=%s", session_id)
    return success(work_service.clear_talks(session_id), "记忆已清空")


@woker.get("/weather", summary="天气查询（经纬度/行政区划编码 二选一）")
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
    return success(work_service.query_weather(location, adcode, weather_type, added_fields, get_md), "天气查询成功")


@woker.get("/geocoder", summary="经纬度查询（地址解析为经纬度）")
def address_to_location(address: str, policy: int = 0):
    """
    调用腾讯地图地理编码接口，把文本地址解析成经纬度
    :param address: 待解析地址，标准模式(policy=0)必须带城市，例如 北京市海淀区彩和坊路海淀西大街74号
    :param policy: 解析策略，0=标准模式(默认) / 1=宽松模式(可省略城市)
        :return: 经纬度、结构化地址、行政区划编码等信息
    """
    logger.info("地址解析：address=%s, policy=%s", address, policy)
    return success(work_service.address_to_location(address, policy), "地址解析成功")


@email_router.post("/generate", summary="第一步：大模型生成邮件内容（不发送）")
def generate_email(prompt: str):
    """
    一句话需求 -> 大模型自动生成邮件主题和正文，仅返回内容供用户编辑确认，不会发送。
    :param prompt: 邮件需求描述，例如"给老师写一封请假邮件，请假两天"
    :return: 生成的邮件内容 {subject: 主题, body: 正文}
    """
    logger.info("生成邮件内容：prompt=%s", prompt)
    return success(email_util.generate_email_content(prompt), "邮件内容已生成")


@email_router.post("/send", summary="第二步：发送用户确认后的邮件")
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
