from openai import OpenAI
import json
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
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,  # 是否流式返回
        reasoning_effort="high",  # 思考强度
        extra_body={"thinking": {"type": "enabled"}}  # 是否思考
    )
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
# 用一个全局字典在内存中保存每个会话的历史消息
# key 是 session_id（会话标识），value 是这个会话的消息列表
# 注意：存在内存里，服务一重启就清空；生产环境建议换成 Redis 等持久化存储
conversation_store: dict[str, list[dict]] = {}


def talks(session_id: str, prompt: str):
    """
    多轮记忆对话：根据 session_id 区分不同的对话，自动带上历史上下文调用 deepseek
    :param session_id: 会话标识，同一个标识就是同一段连续对话
    :param prompt: 用户这一轮说的话
    :return: 大模型这一轮的回复内容
    """
    # 如果是新会话，先初始化一条 system 消息，设定大模型的人设
    if session_id not in conversation_store:
        conversation_store[session_id] = [
            {"role": "system", "content": "你是一个经验丰富的工作助手，会帮助我完成一些任务"},
        ]

    # 取出这个会话的历史消息，并把用户这一轮的输入追加进去
    messages = conversation_store[session_id]
    messages.append({"role": "user", "content": prompt})

    # 把完整的历史消息（含上下文）一起发给 deepseek，模型据此实现"记忆"
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,  # 是否流式返回
        reasoning_effort="high",  # 思考强度
        extra_body={"thinking": {"type": "enabled"}}  # 是否思考
    )

    # 拿到模型回复，并把回复也存进历史，作为下一轮对话的上下文
    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})

    return reply


def clear_talks(session_id: str):
    """
    清空指定会话的历史记忆，相当于重新开始一段全新对话
    :param session_id: 要清空的会话标识
    :return: 操作结果
    """
    if session_id in conversation_store:
        del conversation_store[session_id]
        return {"success": True, "message": f"会话 {session_id} 的记忆已清空"}
    return {"success": False, "message": f"未找到会话 {session_id}"}


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
        response = requests.get(WEATHER_URL, params=params, timeout=10)
        data = response.json()
    except Exception as e:
        # 网络异常或返回的不是合法 JSON 时，统一返回错误信息
        return {"error": f"调用天气接口失败：{e}"}

    # status=0 表示成功，非 0 把腾讯返回的错误信息透传出去
    if data.get("status") != 0:
        return {"error": data.get("message", "天气查询失败"), "raw_response": data}
    return data


def address_to_location(address: str, policy: int = 0):
    """
    调用腾讯地图地理编码接口，把文本地址解析成经纬度
    :param address: 待解析的地址，标准模式(policy=0)必须带城市，例如 "北京市海淀区彩和坊路海淀西大街74号"
    :param policy: 解析策略，0=标准模式(默认,准确率高) / 1=宽松模式(可省略城市)
    :return: 包含经纬度、结构化地址、行政区划编码等信息的 dict
    """
    if not address:
        return {"error": "address（地址）不能为空"}

    # 文档强调：只对 address 单独做 URL 编码，key/policy 等参数不编码
    # 这里手动拼接 URL，用 quote 只编码地址部分，保证符合接口要求
    encoded_address = quote(address)
    url = f"{GEOCODER_URL}?address={encoded_address}&key={TENCENT_MAP_KEY}&policy={policy}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        return {"error": f"调用地理编码接口失败：{e}"}

    if data.get("status") != 0:
        return {"error": data.get("message", "地址解析失败"), "raw_response": data}

    # 解析成功后，把最常用的经纬度单独提取出来，方便前端直接使用
    result = data.get("result", {})
    loc = result.get("location", {})
    return {
        "success": True,
        "lat": loc.get("lat"),                       # 纬度
        "lng": loc.get("lng"),                       # 经度
        "address_components": result.get("address_components"),  # 结构化省市区地址
        "adcode": result.get("ad_info", {}).get("adcode"),       # 行政区划编码
        "reliability": result.get("reliability"),    # 解析可信度(1~10，≥7 可信)
        "level": result.get("level"),                # 解析精度等级(≥9 点位精度优秀)
    }