"""
项目统一配置模块。

作用：在这里集中把 .env 文件里的配置读进来，其它模块只管从这里 import 用，
不用各自去读环境变量，密钥也不再硬编码在源码里。

用法：
    from config import DEEPSEEK_API_KEY, TENCENT_MAP_KEY
"""

import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件，把里面的键值对写入环境变量
# 只要在程序最早被 import 一次即可，重复调用也没副作用
load_dotenv()

# ==================== 大模型 DeepSeek ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ==================== 通义万相 DashScope（文生图） ====================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# ==================== 腾讯地图（天气查询 / 地理编码） ====================
TENCENT_MAP_KEY = os.getenv("TENCENT_MAP_KEY")

# ==================== QQ 邮箱 SMTP ====================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
# 端口在 .env 里是字符串，这里转成 int 方便直接给 smtplib 用
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SMTP_AUTH_CODE = os.getenv("SMTP_AUTH_CODE")
DEFAULT_RECEIVER = os.getenv("DEFAULT_RECEIVER", "786453528@qq.com")

# ==================== 数据库 MySQL ====================
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "student_management_system")

# NL2SQL 只读账号（数据库层面仅授予 SELECT，纵深防御最后一道防线）
DB_READONLY_USER = os.getenv("DB_READONLY_USER", "")
DB_READONLY_PASSWORD = os.getenv("DB_READONLY_PASSWORD", "")

# ==================== 日志系统 ====================
# 全局日志级别：开发阶段用 DEBUG / INFO，生产环境建议用 WARNING。
# .env 里写字符串（如 INFO），这里统一转成大写，方便 log 模块映射成 logging 的级别常量。
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# 日志文件保留天数：只保留最近这么多天，更早的归档文件会被自动清理。
LOG_BACKUP_DAYS = int(os.getenv("LOG_BACKUP_DAYS", "7"))

# ==================== 登录认证 / RBAC ====================
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "change-me-in-env")
AUTH_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "720"))
AUTH_PBKDF2_ITERATIONS = int(os.getenv("AUTH_PBKDF2_ITERATIONS", "600000"))

# ==================== LLM 提取服务 ====================
LLM_EXTRACT_PROVIDER = os.getenv("LLM_EXTRACT_PROVIDER", "deepseek")
