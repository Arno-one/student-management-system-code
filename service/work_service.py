from openai import OpenAI
import json
import time
import requests
from urllib.parse import quote
import dashscope
from dashscope import MultiModalConversation
# 所有密钥统一从 config（.env）读取，不再硬编码在源码里
import config
# 统一日志：替换原先散落的 print，方便归档和排查问题
from util.log import get_logger

# 本模块专用 logger，日志里会带上模块名，便于定位是哪儿打的
logger = get_logger(__name__)

# 腾讯地图开放平台开发者密钥（天气查询、地理编码等接口共用）
TENCENT_MAP_KEY = config.TENCENT_MAP_KEY

client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL)

def evaluation_stu(stu_name,sex,stu_score,style):
    messages = [
        {"role": "system", "content": "你是一个经验丰富的老师，会帮助学生"},
    ]
    if style == style.humor:
        messages.append({"role": "user", "content": f"请幽默的评价{stu_name},性别{sex},他的成绩是{stu_score}"})

    elif style == style.serious:
        messages.append({"role": "user", "content": f"请严肃的评价{stu_name},性别{sex},他的成绩是{stu_score}"})

    elif style == style.incentive:
        messages.append({"role": "user", "content": f"请激励的评价{stu_name},性别{sex},他的成绩是{stu_score}"})

    elif style == style.criticism:
        messages.append({"role": "user", "content": f"请批判的评价{stu_name},性别{sex},他的成绩是{stu_score}"})
    t0 = time.time()
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,  # 是否流式返回
        reasoning_effort="high",  # 思考强度
        extra_body={"thinking": {"type": "enabled"}}  # 是否思考
    )
    cost_ms = int((time.time() - t0) * 1000)
    logger.info("学生评价 LLM 调用完成：student=%s, style=%s, 耗时=%sms", stu_name, style, cost_ms)
    return response.choices[0].message.content

def generate_image(prompt: str):
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
    DASHSCOPE_API_KEY = config.DASHSCOPE_API_KEY
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]
    response = MultiModalConversation.call(
        api_key=DASHSCOPE_API_KEY,
        model="qwen-image-2.0-pro",
        messages=messages,
        result_format='message',
        stream=False,
        watermark=False,
        prompt_extend=True,
        negative_prompt="低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲。",
        size='2048*2048'
    )

    if response.status_code == 200:
        output_data = response.output
        # 原始返回体内容较大，用 debug 级别记录，平时不刷屏，需要时再开 DEBUG 排查
        logger.debug("文生图原始返回：%s", json.dumps(output_data, ensure_ascii=False))

        try:
            image_url = output_data['choices'][0]['message']['content'][0]['image']
            logger.info("文生图成功，已解析出图片URL")
            return {"success": True, "image_url": image_url}
        except (KeyError, IndexError) as e:
            # 解析失败属于异常情况，记 ERROR 方便排查返回结构变化
            logger.error("文生图解析响应失败：%s", e)
            return {"error": "无法解析图片URL", "raw_response": output_data}
    else:
        # 接口本身返回非 200，把关键错误信息一并记进日志，便于对照阿里云错误码文档
        logger.error(
            "文生图接口调用失败 | HTTP状态码=%s | 错误码=%s | 错误信息=%s | 参考文档：%s",
            response.status_code, response.code, response.message,
            "https://help.aliyun.com/zh/model-studio/developer-reference/error-code",
        )
        return {"error": response.message, "code": response.code}

# ============ 多轮记忆对话相关 ============
# 两层记忆架构：
#   内存短期记忆 — 当前活跃会话的消息缓存，服务重启后清空，保证响应速度
#   数据库长期记忆 — 持久化到 MySQL，用于历史会话回溯和跨重启恢复
#
# 工作流程：
#   1. 首次对话 → 从 DB 加载历史消息到内存缓存 → 对话期间读写内存
#   2. 每轮对话后 → 同时写入内存缓存 + 持久化到 DB
#   3. 下次再打开同一会话 → 优先从内存取，内存没有再从 DB 加载

SYSTEM_PROMPT = "你是一个经验丰富的工作助手，会帮助我完成一些任务"

# 内存短期记忆：key=session_id, value={"summary","style","messages":[...]}
# messages 列表中的元素是 {"role":"...", "content":"..."} 的 dict
_session_cache: dict[int, dict] = {}


def _load_session_to_cache(session_id: int, db):
    """将指定会话从数据库加载到内存缓存（如已缓存则跳过）"""
    if session_id in _session_cache:
        return

    from DAO.talk_dao import get_session_by_id, get_messages_by_session

    session = get_session_by_id(session_id, db)
    if not session:
        return

    history = get_messages_by_session(session_id, db)
    cache = {
        "summary": session.summary or "",
        "style": session.style or "",
        "messages": [],
    }

    # 分离 system 消息和对话消息（user/assistant），system 消息不放进缓存消息列表
    for m in history:
        if m.role == "user":
            cache["messages"].append({"role": "user", "content": m.user_content or ""})
        elif m.role == "assistant":
            cache["messages"].append({"role": "assistant", "content": m.ai_content or ""})

    _session_cache[session_id] = cache
    logger.info("会话 %s 已从数据库加载到内存缓存，共 %s 条对话消息", session_id, len(cache["messages"]))


def _build_background(session_id: int) -> str:
    """构建背景板：摘要 + 风格，注入 system prompt 发给大模型"""
    cache = _session_cache.get(session_id, {})
    summary = cache.get("summary", "")
    style = cache.get("style", "")
    if not summary and not style:
        return SYSTEM_PROMPT
    parts = [SYSTEM_PROMPT]
    if summary:
        parts.append(f"【对话背景】{summary}")
    if style:
        parts.append(f"【用户偏好】{style}")
    return "\n".join(parts)


def _summarize_turn(session_id: int, user_msg: str, ai_reply: str, db):
    """每轮对话后调用 DeepSeek 更新会话摘要和用户风格偏好（同时更新内存缓存和数据库）"""
    from DAO.talk_dao import update_session_summary

    prev = _session_cache.get(session_id, {})
    prev_summary = prev.get("summary", "")

    summary_hint = f"当前已归纳的摘要：{prev_summary}" if prev_summary else "这是第一轮对话，请从零开始归纳。"

    summarize_prompt = [
        {"role": "system", "content": (
            "你是一个对话分析助手。根据用户和大模型的最新一轮对话，更新对话主题摘要和用户沟通风格偏好。\n"
            "输出一个 JSON，格式固定为：\n"
            '{"summary": "简短的主题摘要（≤50字）", "style": "偏好的沟通风格关键词（如：简洁/详细/幽默/严肃/技术型等，≤20字）"}\n'
            "只输出 JSON，不要多余内容。"
        )},
        {"role": "user", "content": (
            f"{summary_hint}\n"
            f"用户最新发言：{user_msg}\n"
            f"大模型最新回复：{ai_reply}\n"
            "请输出 JSON。"
        )},
    ]

    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=summarize_prompt,
            stream=False,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            summary = data.get("summary", prev_summary or "")
            style = data.get("style", "")

            # 更新内存缓存
            if session_id in _session_cache:
                _session_cache[session_id]["summary"] = summary
                _session_cache[session_id]["style"] = style

            # 持久化到数据库
            update_session_summary(session_id, summary, style, db)
            logger.info("会话 %s 摘要已更新：summary=%s, style=%s", session_id, summary, style)
    except Exception as e:
        logger.warning("会话 %s 摘要更新失败：%s", session_id, e)


def talks(session_id: int, user_id: str, prompt: str, db):
    """
    多轮记忆对话：
    - 内存短期记忆：活跃会话的消息缓存在内存中，保证响应速度
    - 数据库长期记忆：每轮对话同步写入 DB，历史会话可回溯
    - 背景板：每次对话将 summary 和 style 注入 system prompt
    :param session_id: 会话主键 ID
    :param user_id: 用户标识（校验归属）
    :param prompt: 用户本轮输入
    :param db: 数据库会话
    :return: 大模型回复
    """
    from DAO.talk_dao import (
        get_session_by_id, add_message, touch_session, update_session_title,
    )

    session = get_session_by_id(session_id, db)
    if not session:
        return {"error": f"会话 {session_id} 不存在或已删除"}
    if session.user_id != user_id:
        return {"error": "无权访问该会话"}

    # 确保会话已加载到内存缓存
    _load_session_to_cache(session_id, db)

    cache = _session_cache[session_id]
    is_new = len(cache["messages"]) == 0

    # 拼接背景板（summary + style 作为 system prompt 的一部分）
    system_content = _build_background(session_id)

    # 从内存缓存取对话消息：≤10 条全发，>10 条只取最新 10 条 + 摘要已在背景板中
    dialog_msgs = cache["messages"]
    if len(dialog_msgs) <= 10:
        recent = dialog_msgs
    else:
        recent = dialog_msgs[-10:]

    messages = [{"role": "system", "content": system_content}] + list(recent)

    # 追加本轮用户输入
    messages.append({"role": "user", "content": prompt})

    # 调用大模型
    t0 = time.time()
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    reply = response.choices[0].message.content
    cost_ms = int((time.time() - t0) * 1000)
    logger.info("多轮对话 LLM 调用完成：session_id=%s, 耗时=%sms", session_id, cost_ms)

    # 更新内存短期记忆
    cache["messages"].append({"role": "user", "content": prompt})
    cache["messages"].append({"role": "assistant", "content": reply})

    # 持久化到数据库长期记忆
    add_message(session_id, "user", user_content=prompt, db=db)
    add_message(session_id, "assistant", ai_content=reply, db=db)
    touch_session(session_id, db)

    # 首次对话后自动用第一句话的前30字作为标题
    if is_new:
        title = prompt[:30] + ("..." if len(prompt) > 30 else "")
        update_session_title(session_id, title, db)

    # 更新摘要和风格（内存 + 数据库）
    _summarize_turn(session_id, prompt, reply, db)

    return reply


def clear_talks(session_id: int, user_id: str, db):
    """
    清空指定会话的历史消息（物理删除消息，保留会话壳）
    :param session_id: 会话主键 ID
    :param user_id: 用户标识（用于校验会话归属）
    :param db: 数据库会话
    :return: 操作结果
    """
    from DAO.talk_dao import get_session_by_id, delete_messages_by_session

    session = get_session_by_id(session_id, db)
    if not session:
        logger.warning("清空对话失败：会话 %s 不存在或已删除", session_id)
        return {"success": False, "message": f"会话 {session_id} 不存在或已删除"}
    if session.user_id != user_id:
        logger.warning("清空对话失败：user_id=%s 无权操作会话 %s", user_id, session_id)
        return {"success": False, "message": "无权操作该会话"}

    count = delete_messages_by_session(session_id, db)
    logger.info("清空对话消息：session_id=%s, 删除 %s 条消息", session_id, count)
    return {"success": True, "message": f"会话 {session_id} 的消息已清空"}


# ============ 腾讯地图：天气查询 + 地址转经纬度 ============
# 两个接口的基础地址，统一在这里定义，方便后续维护
WEATHER_URL = "https://apis.map.qq.com/ws/weather/v1/"      # 天气查询接口
GEOCODER_URL = "https://apis.map.qq.com/ws/geocoder/v1/"    # 地址正向地理编码接口（地址→经纬度）


def query_weather(location: str = None, adcode: str = None, weather_type: str = "now",
                  added_fields: str = None, get_md: int = None):
    """
    调用腾讯地图天气接口，查询指定区县的天气
    location 和 adcode 二选一传入（都传时优先用 location）
    :param location: 经纬度坐标，格式 "纬度,经度"，例如 "39.905023,116.724502"
    :param adcode: 行政区划编码，例如 "130681"
    :param weather_type: 天气类型，now=实时(默认) / future=多日预报 / hours=24小时逐时
    :param added_fields: 附加字段，多个用逗号分隔，例如 "alarm,air"
    :param get_md: 仅 future 生效，0=当日+未来3天(默认) / 1=当日+未来6天
    :return: 接口返回的天气数据（dict）
    """
    # location 和 adcode 必须至少传一个，否则腾讯接口会报错，这里提前拦截
    if not location and not adcode:
        logger.warning("天气查询参数缺失：location 和 adcode 均为空")
        return {"error": "location（经纬度）和 adcode（行政区划编码）必须二选一传入"}

    # 组装请求参数，key 是必填项
    params = {
        "key": TENCENT_MAP_KEY,
        "type": weather_type,
    }
    # 优先使用经纬度，没有经纬度再用行政区划编码
    if location:
        params["location"] = location
    else:
        params["adcode"] = adcode
    # 可选参数：有才加，避免传空值影响接口
    if added_fields:
        params["added_fields"] = added_fields
    if get_md is not None:
        params["get_md"] = get_md

    try:
        # requests 会自动对 params 里的参数做 URL 编码，无需手动处理
        t0 = time.time()
        response = requests.get(WEATHER_URL, params=params, timeout=10)
        data = response.json()
        cost_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        # 网络异常或返回的不是合法 JSON 时，统一返回错误信息
        logger.error("天气查询接口调用异常：%s", e)
        return {"error": f"调用天气接口失败：{e}"}

    # status=0 表示成功，非 0 把腾讯返回的错误信息透传出去
    if data.get("status") != 0:
        logger.warning("天气查询接口返回错误：status=%s, message=%s", data.get("status"), data.get("message"))
        return {"error": data.get("message", "天气查询失败"), "raw_response": data}
    logger.info("天气查询成功：location=%s, adcode=%s, type=%s, 耗时=%sms", location, adcode, weather_type, cost_ms)
    return data


def address_to_location(address: str, policy: int = 0):
    """
    调用腾讯地图地理编码接口，把文本地址解析成经纬度
    :param address: 待解析的地址，标准模式(policy=0)必须带城市，例如 "北京市海淀区彩和坊路海淀西大街74号"
    :param policy: 解析策略，0=标准模式(默认,准确率高) / 1=宽松模式(可省略城市)
    :return: 包含经纬度、结构化地址、行政区划编码等信息的 dict
    """
    if not address:
        logger.warning("地址解析参数缺失：address 为空")
        return {"error": "address（地址）不能为空"}

    # 文档强调：只对 address 单独做 URL 编码，key/policy 等参数不编码
    # 这里手动拼接 URL，用 quote 只编码地址部分，保证符合接口要求
    encoded_address = quote(address)
    url = f"{GEOCODER_URL}?address={encoded_address}&key={TENCENT_MAP_KEY}&policy={policy}"

    try:
        t0 = time.time()
        response = requests.get(url, timeout=10)
        data = response.json()
        cost_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        logger.error("地理编码接口调用异常：%s", e)
        return {"error": f"调用地理编码接口失败：{e}"}

    if data.get("status") != 0:
        logger.warning("地理编码接口返回错误：status=%s, message=%s", data.get("status"), data.get("message"))
        return {"error": data.get("message", "地址解析失败"), "raw_response": data}

    # 解析成功后，把最常用的经纬度单独提取出来，方便前端直接使用
    result = data.get("result", {})
    loc = result.get("location", {})
    logger.info("地址解析成功：address=%s, lat=%s, lng=%s, 耗时=%sms", address, loc.get("lat"), loc.get("lng"), cost_ms)
    return {
        "success": True,
        "lat": loc.get("lat"),                       # 纬度
        "lng": loc.get("lng"),                       # 经度
        "address_components": result.get("address_components"),  # 结构化省市区地址
        "adcode": result.get("ad_info", {}).get("adcode"),       # 行政区划编码
        "reliability": result.get("reliability"),    # 解析可信度(1~10，≥7 可信)
        "level": result.get("level"),                # 解析精度等级(≥9 点位精度优秀)
    }