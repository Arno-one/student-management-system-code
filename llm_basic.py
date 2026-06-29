"""
LLM 基础能力模块：模型获取 + 结构化输出。

用法：
    from llm_basic import get_model, structured_complete

注意：NL2SQL 服务（service/nl2sql_service.py）直接使用 openai.OpenAI raw SDK
调用 deepseek-v4-flash，不经过本模块。这是刻意设计：NL2SQL 场景需要 max_tokens=500、
严格 SQL 输出格式、以及自有缓存层，与通用对话/意图分类场景的配置差异较大，
统一封装反而增加复杂度。后续维护时请勿"统一"这两条路径。
"""
import json
from typing import Type, Optional
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from util.log import get_logger

logger = get_logger(__name__)


def get_model(provider: str = "ollama"):
    """
    根据服务商名称返回对应的模型实例。

    好处：切换模型只改一行参数，不需要到处改代码。
    """
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model="qwen2.5:3b-instruct")

    elif provider == "qwen":
        import os
        from dotenv import load_dotenv
        from langchain_openai import ChatOpenAI
        load_dotenv()
        return ChatOpenAI(
            model="qwen-plus",
            api_key=os.getenv("ALIYUN_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    elif provider == "deepseek":
        import os
        from dotenv import load_dotenv
        from langchain_openai import ChatOpenAI
        load_dotenv()
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

    elif provider == "deepseek-v4":
        import os
        from dotenv import load_dotenv
        from langchain_openai import ChatOpenAI
        load_dotenv()
        return ChatOpenAI(
            model="deepseek-v4-flash",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

    else:
        raise ValueError(f"不支持的服务商: {provider}")


def _get_annotation_type(fi) -> type:
    """从 FieldInfo 中提取实际类型（处理 Optional 包装）"""
    from typing import get_origin, get_args
    ann = fi.annotation
    if ann is None:
        return str
    origin = get_origin(ann)
    if origin is not None:
        args = [a for a in get_args(ann) if a is not type(None)]
        if args:
            return args[0]
    return ann


def _build_format_instructions(schema: Type[BaseModel]) -> str:
    """基于 Pydantic schema 生成简洁的 JSON 格式说明"""
    fields_desc = []
    for name, fi in schema.model_fields.items():
        desc = fi.description or name
        typ = _get_annotation_type(fi)
        type_ = "number" if typ in (int, float) else "string"
        fields_desc.append(f'    "{name}": {type_}  // {desc}')
    return "{\n" + ",\n".join(fields_desc) + "\n}"


def structured_complete(
    system_prompt: str,
    user_message: str,
    schema: Type[BaseModel],
    provider: str = "deepseek",
) -> dict:
    """
    调用 LLM 并返回按 schema 校验后的结构化数据。

    Args:
        system_prompt: 系统提示词（不含 JSON 格式说明，会自动追加）
        user_message: 用户消息
        schema: Pydantic 模型类，用于生成 JSON 格式约束和校验输出
        provider: 模型服务商，默认 deepseek

    Returns:
        {"parsed": PydanticModel实例, "error": None}  或
        {"parsed": None, "error": "错误描述"}
    """
    try:
        model = get_model(provider)
        format_instructions = _build_format_instructions(schema)
        full_system = (
            f"{system_prompt}\n\n"
            f"请严格按以下 JSON 格式输出（只输出 JSON，不要有任何额外文字）：\n"
            f"{format_instructions}"
        )

        messages = [SystemMessage(content=full_system), HumanMessage(content=user_message)]
        response = model.invoke(messages)
        raw = response.content.strip()

        # 清理 markdown 代码块包裹
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)

        parsed_dict = json.loads(raw)

        # 过滤 schema 中不存在的 key
        valid_keys = set(schema.model_fields.keys())
        filtered = {k: v for k, v in parsed_dict.items() if k in valid_keys and v is not None}

        validated = schema.model_validate(filtered)
        return {"parsed": validated, "error": None}

    except json.JSONDecodeError as e:
        logger.warning("structured_complete JSON 解析失败：%s", e)
        return {"parsed": None, "error": "模型返回格式异常，请重试"}
    except Exception as e:
        logger.exception("structured_complete 失败：%s", e)
        return {"parsed": None, "error": str(e)}
