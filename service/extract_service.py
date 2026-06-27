"""
LLM 自然语言提取服务 — 公共逻辑

用 structured_complete 把 Pydantic schema 注入 prompt 让 LLM 输出 JSON，
再解析为结构化数据。兼容所有 LLM provider（不依赖 response_format）。
"""
from typing import Optional, Type
from pydantic import BaseModel

from llm_basic import get_model, structured_complete
from config import LLM_EXTRACT_PROVIDER
from util.log import get_logger

logger = get_logger(__name__)

# ==================== 各实体的中文提取 Prompt ====================

STUDENT_EXTRACT_PROMPT = """你是一个学生信息录入助手。从用户的自然语言描述中提取学生信息。

字段说明：
- student_no: 学号，如 "S2024001"
- student_name: 姓名
- class_id: 班级ID，数字。如果用户说"3班"意思是 class_id=3
- gender: 性别，"男"或"女"
- age: 年龄，数字
- native_place: 籍贯，如 "北京市"
- graduate_school: 毕业院校
- major: 专业，如 "计算机科学"
- education: 学历，如 "本科"、"硕士"、"博士"
- admission_time: 入学时间，格式 YYYY-MM-DD
- graduate_time: 毕业时间，格式 YYYY-MM-DD
- advisor_id: 顾问编号，数字

规则：
1. 用户没提到的字段不要出现在 JSON 中，绝对不要编造值
2. "N班" 表示班级ID为N
3. 日期格式统一为 YYYY-MM-DD
4. 只输出 JSON，不要输出任何其他文字"""

STUDENT_UPDATE_EXTRACT_PROMPT = """你是一个学生信息修改助手。从用户的自然语言中提取：要修改哪个学生（定位条件），以及要改哪些字段（变更内容）。

定位字段说明：
- student_id: 学生ID（如果用户直接说了ID数字）
- student_no: 学号
- student_name: 当前姓名（辅助定位，防止改错人）

可变更字段说明（放在 changes 里）：
- class_id: 班级ID，数字
- student_name: 新姓名
- gender: 性别
- age: 年龄，数字
- native_place: 籍贯
- graduate_school: 毕业院校
- major: 专业
- education: 学历
- admission_time: 入学时间，格式 YYYY-MM-DD
- graduate_time: 毕业时间，格式 YYYY-MM-DD
- advisor_id: 顾问编号，数字

规则：
1. 用户没提到的字段不要出现在 JSON 中，绝对不要编造值
2. "N班" 表示班级ID为N
3. 如果没有明确的定位条件（student_id 或 student_no），定位字段不要出现
4. 只输出 JSON，不要输出任何其他文字"""

EMPLOYMENT_EXTRACT_PROMPT = """你是一个就业信息录入助手。从用户的自然语言描述中提取就业信息。

字段说明：
- student_no: 学号，如 "S2024001"
- student_name: 学生姓名
- class_id: 班级ID，数字。如果用户说"3班"意思是 class_id=3
- job_open_time: 就业开放时间，格式 YYYY-MM-DD
- offer_send_time: offer下发时间，格式 YYYY-MM-DD
- company_name: 公司名称
- salary: 薪资，数字（单位：元）

规则：
1. 用户没提到的字段不要出现在 JSON 中，绝对不要编造值
2. "N班" 表示班级ID为N
3. 日期格式统一为 YYYY-MM-DD
4. 只输出 JSON，不要输出任何其他文字"""

SCORE_EXTRACT_PROMPT = """你是一个成绩录入助手。从用户的自然语言描述中提取成绩信息。

字段说明：
- student_no: 学号，如 "S2025001"
- exam_order: 考试次序，正整数，如第1次考试就是1
- score: 成绩，0-100之间的数字

规则：
1. 用户没提到的字段不要出现在 JSON 中，绝对不要编造值
2. "第N次考试" 表示 exam_order=N
3. 只输出 JSON，不要输出任何其他文字"""

# Prompt 注册表
_EXTRACT_PROMPTS = {
    "student": STUDENT_EXTRACT_PROMPT,
    "student_update": STUDENT_UPDATE_EXTRACT_PROMPT,
    "employment": EMPLOYMENT_EXTRACT_PROMPT,
    "score": SCORE_EXTRACT_PROMPT,
}


def extract_fields(
    text: str,
    schema: Type[BaseModel],
    entity: str,
    required_fields: Optional[list[str]] = None,
    provider: Optional[str] = None,
):
    """
    用 LLM 从自然语言文本中提取结构化字段。

    Args:
        text: 用户输入的自然语言
        schema: 提取目标 Pydantic 模型类（全 Optional 字段）
        entity: 实体名，用于选择对应的中文 prompt（如 "student"）
        required_fields: 必填字段名列表，用于检测缺失字段
        provider: 模型服务商，默认用 config.LLM_EXTRACT_PROVIDER

    Returns:
        dict: {"extracted": {...}, "missing_required": [...], "error": None}
    """
    if required_fields is None:
        required_fields = []

    base_prompt = _EXTRACT_PROMPTS.get(entity, "")
    used_provider = provider or LLM_EXTRACT_PROVIDER

    logger.info("开始LLM提取：entity=%s, provider=%s, text_len=%s",
                entity, used_provider, len(text))

    result = structured_complete(
        system_prompt=base_prompt,
        user_message=text,
        schema=schema,
        provider=used_provider,
    )

    if result["error"]:
        logger.warning("LLM 提取失败：entity=%s, error=%s", entity, result["error"])
        return {
            "extracted": None,
            "missing_required": required_fields,
            "error": result["error"],
        }

    validated = result["parsed"]
    extracted_raw = validated.model_dump(exclude_none=True)

    # JSON 安全转换（date/datetime 等类型转字符串）
    import json
    safe = {}
    for k, v in extracted_raw.items():
        try:
            json.dumps({k: v})
            safe[k] = v
        except (TypeError, ValueError):
            safe[k] = str(v)

    # 计算缺失的必填字段
    missing = [f for f in required_fields if f not in safe or safe[f] is None]

    logger.info("提取完成：entity=%s, 提取字段=%s, 缺失必填=%s",
                entity, list(safe.keys()), missing)
    if missing:
        logger.warning("提取结果缺失必填字段：entity=%s, 缺失=%s", entity, missing)
    return {"extracted": safe, "missing_required": missing, "error": None}
