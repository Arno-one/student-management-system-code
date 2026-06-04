"""
调用大模型自动生成邮件内容并通过 QQ 邮箱 SMTP 发送的工具模块。

整体流程：用户给一句话需求(prompt) -> 调用 DeepSeek 大模型生成"邮件主题 + 正文"
        -> 用 smtplib 通过 QQ 邮箱 SMTP 服务器把邮件发出去。
"""

import json
import smtplib
# 注意：本文件虽然叫 email.py，但它是作为 util.email 这个子模块被导入的，
# 下面的 from email.xxx 走的是 Python 标准库的 email 包，不会和本文件冲突。
from email.mime.text import MIMEText
from email.header import Header

from openai import OpenAI
# 密钥/邮箱配置统一从 config（.env）读取，不再硬编码
import config

# ============ 大模型客户端（沿用项目里 DeepSeek 的调用方式）============
client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL)

# ============ QQ 邮箱 SMTP 相关配置（均来自 .env）============
SMTP_HOST = config.SMTP_HOST            # QQ 邮箱发件服务器
SMTP_PORT = config.SMTP_PORT            # 使用 SSL 的端口（465 或 587，这里用 465）
SENDER_EMAIL = config.SENDER_EMAIL      # 发件邮箱（完整地址）
SMTP_AUTH_CODE = config.SMTP_AUTH_CODE  # 邮箱授权码（不是登录密码，是开通SMTP后生成的授权码）
DEFAULT_RECEIVER = config.DEFAULT_RECEIVER  # 默认收件邮箱


def generate_email_content(prompt: str) -> dict:
    """
    调用大模型，根据一句话需求生成邮件的"主题"和"正文"。

    :param prompt: 用户的需求描述，例如"给老师写一封请假邮件，请假两天"
    :return: 字典 {"subject": 邮件主题, "body": 邮件正文}
    """
    # system 设定大模型的角色，并要求它严格用 JSON 返回，方便我们解析出主题和正文
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的邮件写作助手。在信的开头会说明自己是谁，并根据用户需求生成一封完整的邮件，以幽默但不失风度的风格来写信，要夸一夸寄信的对象。"
                "只返回一个 JSON 对象，格式严格为：{\"subject\": \"邮件主题\", \"body\": \"邮件正文\"}，"
                "不要输出 JSON 以外的任何多余文字、也不要用 markdown 代码块包裹。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,  # 是否流式返回
        reasoning_effort="high",  # 思考强度
        extra_body={"thinking": {"type": "enabled"}}  # 是否思考
    )

    # 取出模型返回的文本
    raw = response.choices[0].message.content.strip()

    # 大模型有时会用 ```json ... ``` 把结果包起来，这里做个兜底清理
    if raw.startswith("```"):
        raw = raw.strip("`")            # 去掉首尾的反引号
        raw = raw.replace("json", "", 1).strip()  # 去掉可能的 json 标记

    # 尝试把模型返回的 JSON 解析成字典；万一解析失败，就把整段文本当正文，用默认主题
    try:
        data = json.loads(raw)
        subject = data.get("subject", "来自学生管理系统的邮件")
        body = data.get("body", raw)
    except json.JSONDecodeError:
        subject = "来自学生管理系统的邮件"
        body = raw

    return {"subject": subject, "body": body}


def send_email(subject: str, body: str, receiver: str = DEFAULT_RECEIVER) -> dict:
    """
    通过 QQ 邮箱 SMTP 服务器发送一封 HTML 邮件（支持加粗、列表、换行等富文本排版）。

    :param subject: 邮件主题
    :param body: 邮件正文（HTML 字符串）
    :param receiver: 收件邮箱，默认发给 DEFAULT_RECEIVER
    :return: 操作结果字典
    """
    # 兼容老的纯文本：如果传进来的正文里没有任何 HTML 标签，
    # 就把换行符转成 <br>，避免 HTML 邮件里换行丢失
    if "<" not in body and ">" not in body:
        body = body.replace("\n", "<br>")
    # 套一层基础样式，让邮件在客户端里排版更美观
    html_body = (
        '<div style="font-family:微软雅黑,Microsoft YaHei,Arial,sans-serif;'
        'font-size:15px;line-height:1.8;color:#333;">'
        f'{body}</div>'
    )
    # 构造一封 HTML 邮件，html 表示富文本，utf-8 保证中文不乱码
    message = MIMEText(html_body, "html", "utf-8")
    message["From"] = Header(SENDER_EMAIL)        # 发件人
    message["To"] = Header(receiver)              # 收件人
    message["Subject"] = Header(subject, "utf-8")  # 邮件主题

    try:
        # 用 SSL 方式连接 QQ 邮箱发件服务器（465 端口走 SSL）
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            # 用"完整邮箱地址 + 授权码"登录
            smtp.login(SENDER_EMAIL, SMTP_AUTH_CODE)
            # 发送邮件：发件人、收件人、邮件内容
            smtp.sendmail(SENDER_EMAIL, [receiver], message.as_string())
        return {"success": True, "message": f"邮件已成功发送至 {receiver}"}
    except smtplib.SMTPException as e:
        # 捕获 SMTP 相关异常，把错误信息返回出去，方便排查
        return {"success": False, "message": f"邮件发送失败：{e}"}


def ai_send_email(prompt: str, receiver: str = DEFAULT_RECEIVER) -> dict:
    """
    一站式：根据需求让大模型生成邮件内容，并直接发送出去。

    :param prompt: 用户的需求描述
    :param receiver: 收件邮箱，默认发给 DEFAULT_RECEIVER
    :return: 包含生成内容和发送结果的字典
    """
    # 第一步：大模型生成主题和正文
    content = generate_email_content(prompt)
    # 第二步：把生成的内容发出去
    result = send_email(content["subject"], content["body"], receiver)

    # 把生成的内容也一并返回，方便前端展示"发了什么"
    return {
        "subject": content["subject"],
        "body": content["body"],
        "receiver": receiver,
        "send_result": result,
    }
