import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# 让脚本能找到项目根目录，从而 import 到 util.log（直接运行本脚本时也能用统一日志）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util.log import setup_logging, get_logger

# 从项目根目录的 .env 读取密钥（直接运行本脚本时也能找到）
load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))


def main():
    """直接运行本脚本时，做一次最简单的大模型对话测试"""
    # 独立运行需要自己初始化一次日志系统，结果统一进 logs 目录
    setup_logging()
    logger = get_logger(__name__)

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是一个经验丰富的工作助手，会帮助我完成一些任务"},
            {"role": "user", "content": "你好，请简单介绍一下你自己"},
        ],
        stream=False,  # 是否流式返回
        reasoning_effort="high",  # 思考强度
        extra_body={"thinking": {"type": "enabled"}}  # 是否思考
    )

    # 原先用 print 直接打印，现在统一走日志，方便归档
    logger.info("大模型回复：%s", response.choices[0].message.content)


if __name__ == "__main__":
    main()