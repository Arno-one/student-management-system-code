"""Agent 执行器 — 按计划执行步骤，产出最终响应（同步版 + 流式版）"""
import json
import time
from collections.abc import Generator
from sqlalchemy.orm import Session

from llm_basic import get_model
from langchain_core.messages import SystemMessage, HumanMessage

from agent_system.schemas.task_state import ExecutionPlan
from agent_system.schemas.agent_response import AgentChatResponse, ToolCallRecord
from agent_system.prompts.persona_prompt import PERSONA_REGISTRY
from agent_system.tools.base import ToolContext
from agent_system.tools import (
    ScoreTool, StudentTool, RagTool, Nl2sqlTool, WeatherTool, ImageTool, EmailTool,
    CommutePlanTool, NearbyServiceTool, _resolve_student,
)
from agent_system.hitl.escalation_rules import build_hitl_payload, get_hitl_rule
from agent_system.hitl.hitl_manager import pause_execution
from agent_system.hitl.hitl_schema import HitlState
from util.log import get_logger

logger = get_logger(__name__)

# ==================== 工具分发表（类实例） ====================

_TOOL_REGISTRY: dict[str, object] = {
    "score_tool": ScoreTool(),
    "rag_tool": RagTool(),
    "nl2sql_tool": Nl2sqlTool(),
    "student_tool": StudentTool(),
    "weather_tool": WeatherTool(),
    "image_tool": ImageTool(),
    "email_tool": EmailTool(),
    "commute_plan_tool": CommutePlanTool(),
    "nearby_service_tool": NearbyServiceTool(),
}

# 读操作工具名集合（仅这些工具参与 session 级缓存）
_CACHEABLE_TOOLS = {"score_tool", "student_tool", "rag_tool"}
# session 级工具结果缓存: {session_id: {cache_key: result_dict}}
_SESSION_CACHE: dict[str, dict[str, dict]] = {}


def _sse_event(event: str, data: dict | str) -> str:
    if isinstance(data, str):
        data = {"text": data}
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_persona_prompt(persona: str) -> str:
    entry = PERSONA_REGISTRY.get(persona)
    if entry:
        return entry["system_prompt"]
    return PERSONA_REGISTRY["academic_mentor"]["system_prompt"]


def _build_summarize_messages(context: dict, instruction: str, persona: str) -> tuple[str, str]:
    persona_prompt = _get_persona_prompt(persona)
    ctx_parts = []
    for key, val in context.items():
        if not val:
            continue
        if key == "rag_tool" and val.get("success") and val.get("chunks"):
            # 知识检索：用带来源编号的格式化文本替代 raw JSON
            chunk_texts = []
            for i, chunk in enumerate(val["chunks"], 1):
                source_type = chunk.get("source_type", "")
                file_name = chunk.get("file_name", "未知")
                text = chunk.get("text", "")
                if source_type == "faq":
                    chunk_texts.append(f'[来源 {i} | FAQ | {file_name}]\n{text}')
                elif source_type == "qa":
                    chunk_texts.append(f'[来源 {i} | 问答对 | {file_name}]\n{text}')
                else:
                    chunk_texts.append(f'[来源 {i} | 文档 | {file_name}]\n{text}')
            ctx_parts.append("【知识检索结果】\n\n" + "\n\n".join(chunk_texts))
        else:
            ctx_parts.append(f"【{key}】\n{json.dumps(val, ensure_ascii=False, indent=2)}")
    ctx_text = "\n\n".join(ctx_parts) if ctx_parts else "（无工具返回数据）"

    system_prompt = (
        f"{persona_prompt}\n\n"
        f"当前任务：{instruction}\n"
        f"请基于以下数据生成回复。回复要自然、易读、符合你的角色风格。"
        f"如果数据中有成绩信息，用清晰的方式呈现分数和趋势。"
        f"如果是知识检索结果，回答时引用来源编号（如 [来源 1]），并结合内容回答用户问题。"
        f"如果是天气数据，用口语化的方式播报。"
        f"如果是通勤规划结果，说明起点、终点、出行方式、预计耗时、距离和天气辅助提醒。"
        f"如果是周边服务结果，说明查询中心、范围和结果数量，不要做最好、最安全、最便宜等绝对判断。"
    )
    return system_prompt, f"工具返回数据：\n{ctx_text}"


def _build_reply_messages(message: str, persona: str) -> tuple[str, str]:
    persona_prompt = _get_persona_prompt(persona)
    system_prompt = (
        f"{persona_prompt}\n\n"
        f"请用温和、自然的方式回复用户。如果是情绪支持场景，先共情再给温和建议。"
        f"回复控制在 2-3 段以内。"
    )
    return system_prompt, message


# ==================== ToolContext 构建 ====================

def _build_tool_context(
    step, user: dict, db: Session, db_readonly: Session | None,
    executed: dict[str, dict], student_no: str | None,
) -> ToolContext:
    """构建工具执行上下文，自动从 inputs_from 引用的上游结果中按字段名匹配参数"""
    params: dict = dict(step.params) if step.params else {}

    # 从 inputs_from 引用的上游结果中自动匹配字段
    for upstream_name in (step.inputs_from or []):
        upstream_result = executed.get(upstream_name, {})
        if upstream_result:
            tool = _TOOL_REGISTRY.get(step.tool_name)
            if tool and hasattr(tool, "inputs_schema"):
                for field_name in tool.inputs_schema:
                    if field_name not in params and field_name in upstream_result:
                        params[field_name] = upstream_result[field_name]

    # 注入默认值
    if "student_no" not in params and student_no:
        params["student_no"] = student_no
    if "current_username" not in params:
        params["current_username"] = user.get("username", "")
    if "user_id" not in params:
        params["user_id"] = user.get("username", "")

    return ToolContext(
        params=params,
        upstream_results=executed,
        user=user,
        db=db,
        db_readonly=db_readonly,
    )


# ==================== Session 级工具结果缓存 ====================

def _cache_key_for(tool_name: str, ctx: ToolContext) -> str:
    """构建缓存 key: tool_name + 参数指纹"""
    params_str = json.dumps(ctx.params, ensure_ascii=False, sort_keys=True)
    return f"{tool_name}:{params_str}"


def _cache_get(session_id: str, cache_key: str) -> dict | None:
    """从 session 缓存中查工具结果"""
    session_cache = _SESSION_CACHE.get(session_id, {})
    return session_cache.get(cache_key)


def _cache_set(session_id: str, cache_key: str, result: dict) -> None:
    """将工具结果写入 session 缓存"""
    if session_id not in _SESSION_CACHE:
        _SESSION_CACHE[session_id] = {}
    _SESSION_CACHE[session_id][cache_key] = result


# ==================== 流式 LLM 调用 ====================

def _llm_stream_summarize(
    context: dict, instruction: str, persona: str, provider: str = "deepseek",
) -> Generator[str, None, None]:
    system_prompt, user_content = _build_summarize_messages(context, instruction, persona)
    try:
        model = get_model(provider)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        for chunk in model.stream(messages):
            text = chunk.content
            if isinstance(text, str) and text:
                yield text
    except Exception as e:
        logger.exception("LLM 流式总结失败: %s", e)
        yield "抱歉，我在分析数据时遇到了一些问题。请稍后再试。"


def _llm_stream_reply(
    message: str, persona: str, fallback_response: str | None = None, provider: str = "deepseek",
) -> Generator[str, None, None]:
    system_prompt, user_content = _build_reply_messages(message, persona)
    try:
        model = get_model(provider)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        for chunk in model.stream(messages):
            text = chunk.content
            if isinstance(text, str) and text:
                yield text
    except Exception as e:
        logger.exception("LLM 流式对话回复失败: %s", e)
        yield fallback_response or "你好！我是学业导师，有什么可以帮你的吗？"


# ==================== 同步 LLM 调用 ====================

def _llm_summarize(context: dict, instruction: str, persona: str, provider: str = "deepseek") -> str:
    system_prompt, user_content = _build_summarize_messages(context, instruction, persona)
    try:
        model = get_model(provider)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        response = model.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.exception("LLM 总结失败: %s", e)
        return "抱歉，我在分析数据时遇到了一些问题。请稍后再试。"


def _llm_reply(message: str, persona: str, fallback_response: str | None = None, provider: str = "deepseek") -> str:
    system_prompt, user_content = _build_reply_messages(message, persona)
    try:
        model = get_model(provider)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        response = model.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.exception("LLM 对话回复失败: %s", e)
        return fallback_response or "你好！我是学业导师，有什么可以帮你的吗？"


# ==================== 通用工具执行 ====================

def _execute_step(step, tool, ctx: ToolContext, user: dict) -> dict:
    """通用工具执行：通过 BaseTool.run(ctx) 分发，不再硬编码 if/elif"""
    if step.tool_name == "student_tool":
        return _resolve_student(
            db=ctx.db, current_username=user["username"],
            student_no_override=ctx.params.get("student_no_override"),
        )
    return tool.run(ctx)


def _result_status(result: dict) -> str:
    """保留工具返回的 partial_success/empty/awaiting_confirmation 等业务状态。"""
    status = result.get("status")
    if status in {"partial_success", "awaiting_confirmation", "clarification", "empty"}:
        return status
    return "success" if result.get("success", False) else "error"


# ==================== 流式主执行函数 ====================

def run_plan_stream(
    plan: ExecutionPlan,
    user: dict,
    db: Session,
    db_readonly: Session | None = None,
    student_no_override: str | None = None,
    original_message: str = "",
    provider: str = "deepseek",
    session_id: int | None = None,
) -> Generator[str, None, dict]:
    tool_records: list[ToolCallRecord] = []
    executed: dict[str, dict] = {}
    target_student_no = student_no_override

    yield _sse_event("intent", {"intent": plan.intent, "persona": plan.persona})

    # 先处理 student_tool（身份解析）
    for step in plan.steps:
        if step.tool_name != "student_tool":
            continue
        yield _sse_event("tool_start", {"tool_name": "student_tool"})
        resolve_result = _resolve_student(
            db=db, current_username=user["username"],
            student_no_override=student_no_override,
        )
        status = "success" if resolve_result["found"] else "error"
        summary = (
            f"解析到学生 {resolve_result.get('student_name', '?')}"
            if resolve_result["found"] else resolve_result.get("error")
        )
        tool_records.append(ToolCallRecord(tool_name="student_tool", status=status, summary=summary))
        yield _sse_event("tool_end", {"tool_name": "student_tool", "status": status, "summary": summary})
        executed["student_tool"] = resolve_result
        if resolve_result["found"]:
            target_student_no = resolve_result["student_no"]

    # 执行其他工具步骤（通用分发）
    for step in plan.steps:
        if step.tool_name == "student_tool":
            continue

        tool = _TOOL_REGISTRY.get(step.tool_name)
        if not tool:
            logger.warning("未知工具: %s，跳过", step.tool_name)
            tool_records.append(ToolCallRecord(
                tool_name=step.tool_name, status="error", summary=f"未知工具: {step.tool_name}",
            ))
            continue

        yield _sse_event("tool_start", {"tool_name": step.tool_name})
        logger.info("流式执行工具: %s", step.tool_name)

        try:
            ctx = _build_tool_context(step, user, db, db_readonly, executed, target_student_no)
            # 工具的"自然语言输入"类参数（question/prompt/location_text 等）如果未填充，默认注入原始消息
            _NL_PARAM_NAMES = {"question", "prompt", "location_text", "request_text"}
            for field_name in _NL_PARAM_NAMES:
                if field_name in tool.inputs_schema and not ctx.params.get(field_name):
                    ctx.params[field_name] = original_message or ""

            # session 级缓存：读操作工具先查缓存
            sid = str(session_id) if session_id else "default"
            cache_key = _cache_key_for(step.tool_name, ctx)
            if step.tool_name in _CACHEABLE_TOOLS:
                cached = _cache_get(sid, cache_key)
                if cached is not None:
                    logger.info("缓存命中: %s", cache_key)
                    result = cached
                    result["_cached"] = True
                else:
                    result = _execute_step(step, tool, ctx, user)
                    _cache_set(sid, cache_key, result)
            else:
                result = _execute_step(step, tool, ctx, user)

            status = _result_status(result)
            summary = _tool_summary(step.tool_name, result)
            tool_records.append(ToolCallRecord(
                tool_name=step.tool_name, status=status, summary=summary,
            ))
            yield _sse_event("tool_end", {
                "tool_name": step.tool_name, "status": status, "summary": summary,
            })
            executed[step.tool_name] = result

            # HITL 检测：规则驱动的高风险操作确认
            if result.get("status") == "awaiting_confirmation":
                rule = get_hitl_rule(step.tool_name)
                preview = result.get("preview", {})
                expires_at = time.time() + rule.timeout_seconds
                yield _sse_event(
                    "awaiting_confirmation",
                    build_hitl_payload(step.tool_name, preview, rule, expires_at, step_id=step.step_id),
                )
                # 保存暂停状态供后续恢复
                pause_execution(
                    task_id=str(session_id) if session_id else "default",
                    step_id=step.step_id,
                    state=HitlState(
                        tool_name=step.tool_name,
                        preview=preview,
                        timeout_seconds=rule.timeout_seconds,
                        expires_at=expires_at,
                        risk_level=rule.risk_level,
                        confirm_title=rule.confirm_title,
                        confirm_message=rule.confirm_message,
                    ),
                )
                # HITL 场景下流在此结束，后续由 /agent/step/confirm 恢复
                break

        except Exception as e:
            logger.exception("工具执行异常: tool=%s, error=%s", step.tool_name, e)
            tool_records.append(ToolCallRecord(tool_name=step.tool_name, status="error", summary=str(e)))
            yield _sse_event("tool_end", {"tool_name": step.tool_name, "status": "error", "summary": str(e)})
            executed[step.tool_name] = {"success": False, "error": str(e)}

    # 生成最终回复
    sources = None
    full_reply = ""
    hitl_pending = any(
        r.get("status") == "awaiting_confirmation"
        for r in executed.values() if isinstance(r, dict)
    )

    if hitl_pending:
        full_reply = "请确认以上邮件预览内容。"
        yield _sse_event("chunk", full_reply)
        sources = None
    elif plan.need_llm_summary and plan.steps:
        full_reply = yield from _stream_reply_from_llm(
            plan=plan, context=executed, persona=plan.persona, provider=provider,
        )
        sources = _extract_sources(executed)
    elif plan.fallback_response is not None:
        full_reply = yield from _stream_reply_direct(
            plan=plan, original_message=original_message, provider=provider,
        )
        sources = None
    elif not plan.steps:
        full_reply = "你好！我是学业导师，有什么可以帮你的吗？"
        yield _sse_event("chunk", full_reply)
    else:
        full_reply = _format_raw_results(executed)
        yield _sse_event("chunk", full_reply)
        sources = _extract_sources(executed)

    tc_list = (
        [{"tool_name": t.tool_name, "status": t.status, "summary": t.summary} for t in tool_records]
        if tool_records else None
    )
    cards = _extract_cards(executed)
    tool_monitoring = _extract_tool_monitoring(executed)
    done_data = {
        "intent": plan.intent,
        "persona": plan.persona,
        "tool_calls": tc_list,
        "sources": sources,
        "cards": cards,
        "tool_monitoring": tool_monitoring,
        "reply": full_reply,
    }
    yield _sse_event("done", done_data)

    logger.info("流式执行完成: intent=%s, tools=%s, reply_len=%s",
                plan.intent, [t.tool_name for t in tool_records], len(full_reply))

    return {
        "session_meta": {
            "intent": plan.intent,
            "full_reply": full_reply,
            "tool_calls": tc_list,
            "sources": sources,
            "cards": cards,
        }
    }


def _stream_reply_from_llm(plan, context, persona, provider) -> Generator[str, None, str]:
    full = ""
    for text_chunk in _llm_stream_summarize(
        context=context,
        instruction=plan.summary_instruction or "请总结以上数据",
        persona=persona,
        provider=provider,
    ):
        full += text_chunk
        yield _sse_event("chunk", text_chunk)
    return full


def _stream_reply_direct(plan, original_message, provider) -> Generator[str, None, str]:
    full = ""
    for text_chunk in _llm_stream_reply(
        message=original_message or plan.fallback_response or "",
        persona=plan.persona,
        fallback_response=plan.fallback_response,
        provider=provider,
    ):
        full += text_chunk
        yield _sse_event("chunk", text_chunk)
    return full


# ==================== 同步主执行函数 ====================

def run_plan(
    plan: ExecutionPlan,
    user: dict,
    db: Session,
    db_readonly: Session | None = None,
    student_no_override: str | None = None,
    original_message: str = "",
    provider: str = "deepseek",
    session_id: int | None = None,
) -> AgentChatResponse:
    tool_records: list[ToolCallRecord] = []
    executed: dict[str, dict] = {}
    target_student_no = student_no_override

    # 先处理 student_tool
    for step in plan.steps:
        if step.tool_name != "student_tool":
            continue
        resolve_result = _resolve_student(
            db=db, current_username=user["username"],
            student_no_override=student_no_override,
        )
        tool_records.append(ToolCallRecord(
            tool_name="student_tool",
            status="success" if resolve_result["found"] else "error",
            summary=(
                f"解析到学生 {resolve_result.get('student_name', '?')}"
                if resolve_result["found"] else resolve_result.get("error")
            ),
        ))
        executed["student_tool"] = resolve_result
        if resolve_result["found"]:
            target_student_no = resolve_result["student_no"]

    # 通用分发执行其他步骤
    for step in plan.steps:
        if step.tool_name == "student_tool":
            continue

        tool = _TOOL_REGISTRY.get(step.tool_name)
        if not tool:
            logger.warning("未知工具: %s，跳过", step.tool_name)
            tool_records.append(ToolCallRecord(
                tool_name=step.tool_name, status="error", summary=f"未知工具: {step.tool_name}",
            ))
            continue

        try:
            ctx = _build_tool_context(step, user, db, db_readonly, executed, target_student_no)
            if "question" in tool.inputs_schema and "question" not in ctx.params:
                ctx.params["question"] = original_message or ""
            if "prompt" in tool.inputs_schema and "prompt" not in ctx.params:
                ctx.params["prompt"] = original_message or ""
            if "request_text" in tool.inputs_schema and "request_text" not in ctx.params:
                ctx.params["request_text"] = original_message or ""

            result = _execute_step(step, tool, ctx, user)
            status = _result_status(result)
            tool_records.append(ToolCallRecord(
                tool_name=step.tool_name,
                status=status,
                summary=_tool_summary(step.tool_name, result),
            ))
            executed[step.tool_name] = result

            if result.get("status") == "awaiting_confirmation":
                break  # HITL 暂停，不继续执行

        except Exception as e:
            logger.exception("工具执行异常: tool=%s, error=%s", step.tool_name, e)
            tool_records.append(ToolCallRecord(tool_name=step.tool_name, status="error", summary=str(e)))
            executed[step.tool_name] = {"success": False, "error": str(e)}

    # 生成回复
    hitl_pending = any(
        r.get("status") == "awaiting_confirmation"
        for r in executed.values() if isinstance(r, dict)
    )

    if hitl_pending:
        reply = "请确认以上邮件预览内容。"
        sources = None
    elif plan.need_llm_summary and plan.steps:
        reply = _llm_summarize(
            context=executed, instruction=plan.summary_instruction or "请总结以上数据",
            persona=plan.persona, provider=provider,
        )
        sources = _extract_sources(executed)
    elif plan.fallback_response is not None:
        reply = _llm_reply(
            message=original_message or plan.fallback_response or "",
            persona=plan.persona, fallback_response=plan.fallback_response, provider=provider,
        )
        sources = None
    elif not plan.steps:
        reply = "你好！我是学业导师，有什么可以帮你的吗？"
        sources = None
    else:
        reply = _format_raw_results(executed)
        sources = _extract_sources(executed)
    cards = _extract_cards(executed)
    tool_monitoring = _extract_tool_monitoring(executed)

    logger.info("执行完成: intent=%s, tools=%s, reply_len=%s",
                plan.intent, [r.tool_name for r in tool_records], len(reply))

    return AgentChatResponse(
        reply=reply, intent=plan.intent, persona=plan.persona,
        tool_calls=tool_records if tool_records else None,
        sources=sources, cards=cards, tool_monitoring=tool_monitoring, session_id=0,
    )


# ==================== 辅助函数 ====================

def _tool_summary(tool_name: str, result: dict) -> str:
    cache_suffix = "（缓存）" if result.get("_cached") else ""
    if tool_name == "score_tool":
        total = result.get("total", 0)
        base = f"查询到 {total} 条成绩记录" if total > 0 else "未查询到成绩记录"
    elif tool_name == "rag_tool":
        total = result.get("total", 0)
        base = f"检索到 {total} 个相关片段" if total > 0 else "未检索到相关内容"
    elif tool_name == "nl2sql_tool":
        rows = result.get("row_count", 0)
        if rows > 0:
            base = f"查询返回 {rows} 行数据"
        else:
            sql = result.get("sql", "")
            base = f"查询执行成功，但数据库中暂无符合条件的数据" if sql else "查询无结果"
    elif tool_name == "student_tool":
        base = f"学生: {result.get('student_name', '?')}" if result.get("found") else "未找到学生"
    elif tool_name == "weather_tool":
        if result.get("success"):
            loc = result.get("location_text", "")
            base = f"已查询 {loc} 天气信息" if loc else "天气查询完成"
        else:
            base = f"天气查询失败: {result.get('error', '')}"
    elif tool_name == "image_tool":
        if result.get("success"):
            base = "图片已生成"
        else:
            base = f"文生图失败: {result.get('error', '')}"
    elif tool_name == "commute_plan_tool":
        if result.get("success"):
            ok_count = sum(1 for item in result.get("routes", []) if item.get("success"))
            total = len(result.get("routes", []))
            suffix = "，部分方式失败" if result.get("status") == "partial_success" else ""
            base = f"已规划 {result.get('origin_text', '')} 到 {result.get('destination_text', '')} 的通勤路线（{ok_count}/{total}）{suffix}"
        else:
            base = f"通勤规划失败: {result.get('error', '')}"
    elif tool_name == "nearby_service_tool":
        if result.get("status") == "empty":
            base = f"未查到 {result.get('center_name', '')} 附近的 {result.get('query', '')}"
        elif result.get("success"):
            base = f"已查询 {result.get('center_name', '')} 附近的 {result.get('query', '')}，返回 {result.get('result_count', 0)} 条"
        else:
            base = f"周边服务查询失败: {result.get('error', '')}"
    elif tool_name == "email_tool":
        if result.get("status") == "awaiting_confirmation":
            preview = result.get("preview", {})
            base = f"邮件预览已生成，等待确认发送至 {preview.get('receiver', '')}"
        else:
            base = "邮件已生成"
    else:
        base = "完成"
    return base + cache_suffix


def _extract_sources(context: dict) -> list[dict] | None:
    rag_result = context.get("rag_tool")
    if not rag_result or not rag_result.get("success"):
        return None
    sources = []
    for c in rag_result.get("chunks", [])[:5]:
        sources.append({
            "file_name": c.get("file_name", ""),
            "source_type": c.get("source_type", ""),
            "text_preview": c.get("text_preview", ""),
            "score": c.get("score"),
        })
    return sources if sources else None


def _extract_cards(context: dict) -> list[dict] | None:
    """从工具结构化结果中提取前端可直接渲染的卡片数据。"""
    cards = []
    weather_result = context.get("weather_tool")
    if isinstance(weather_result, dict) and weather_result.get("success"):
        # 卡片保留原始天气结构，前端组件负责兼容 REST/MCP 的不同字段形态。
        cards.append({
            "type": "weather",
            "card_version": 1,
            "data": {
                "provider": weather_result.get("provider"),
                "fallback_reason": weather_result.get("fallback_reason"),
                "location_text": weather_result.get("location_text"),
                "lat": weather_result.get("lat"),
                "lng": weather_result.get("lng"),
                "adcode": weather_result.get("adcode"),
                "geocode": weather_result.get("geocode"),
                "weather": weather_result.get("weather", {}),
            },
        })
    image_result = context.get("image_tool")
    if isinstance(image_result, dict) and image_result.get("success") and image_result.get("image_url"):
        cards.append({
            "type": "image",
            "card_version": 1,
            "data": {
                "provider": image_result.get("provider"),
                "model": image_result.get("model"),
                "prompt": image_result.get("prompt"),
                "image_url": image_result.get("image_url"),
            },
        })
    commute_result = context.get("commute_plan_tool")
    if isinstance(commute_result, dict) and commute_result.get("success"):
        cards.append({
            "type": "route",
            "card_version": 1,
            "data": {
                "provider": commute_result.get("provider"),
                "status": commute_result.get("status"),
                "origin_text": commute_result.get("origin_text"),
                "destination_text": commute_result.get("destination_text"),
                "origin": commute_result.get("origin"),
                "destination": commute_result.get("destination"),
                "travel_modes": commute_result.get("travel_modes", []),
                "departure_time_text": commute_result.get("departure_time_text"),
                "routes": commute_result.get("routes", []),
                "weather_reminder": commute_result.get("weather_reminder"),
            },
        })
    nearby_result = context.get("nearby_service_tool")
    if isinstance(nearby_result, dict) and nearby_result.get("success"):
        cards.append({
            "type": "poi_list",
            "card_version": 1,
            "data": {
                "query": nearby_result.get("query"),
                "center": nearby_result.get("center"),
                "radius_meters": nearby_result.get("radius_meters"),
                "provider": nearby_result.get("provider"),
                "fallback_used": nearby_result.get("fallback_used", False),
                "items": nearby_result.get("items", []),
            },
        })
    return cards or None


def _extract_tool_monitoring(context: dict) -> dict | None:
    """提取轻量监控字段，后续监控面板直接消费这份结构。"""
    monitoring = {}
    nearby_result = context.get("nearby_service_tool")
    if isinstance(nearby_result, dict):
        monitoring["nearby_service_tool"] = {
            "intent": "nearby_service",
            "status": nearby_result.get("status"),
            "provider": nearby_result.get("provider"),
            "fallback_used": nearby_result.get("fallback_used", False),
            "query": nearby_result.get("query"),
            "center_name": nearby_result.get("center_name"),
            "radius_meters": nearby_result.get("radius_meters"),
            "result_count": nearby_result.get("result_count", 0),
            "error_code": nearby_result.get("error_code", ""),
            "error_message": nearby_result.get("error_message", ""),
        }
    return monitoring or None


def _format_raw_results(context: dict) -> str:
    parts = []
    for key, val in context.items():
        if not val or not isinstance(val, dict):
            continue
        if val.get("success"):
            if key == "nl2sql_tool":
                cols = val.get("columns", [])
                rows = val.get("rows", [])
                sql = val.get("sql", "")
                if len(rows) == 0:
                    parts.append(f"执行了以下查询：\n```sql\n{sql}\n```")
                    parts.append("数据库中没有符合该条件的数据。建议检查筛选条件或换个问法试试。")
                else:
                    parts.append(f"查询结果（{len(rows)} 条）：")
                    parts.append(" | ".join(cols))
                    for row in rows[:20]:
                        parts.append(" | ".join(str(c) for c in row))
            elif key == "score_tool":
                scores = val.get("scores", [])
                parts.append(f"成绩记录（{len(scores)} 条）：")
                for s in scores:
                    parts.append(f"第{s['exam_order']}次考试: {s['score']}分")
            elif key == "weather_tool":
                weather = val.get("weather", {})
                for label, data in weather.items():
                    parts.append(f"【{label}】{json.dumps(data, ensure_ascii=False, indent=2)}")
            elif key == "image_tool":
                prompt = val.get("prompt", "")
                parts.append("图片已经生成，请查看下方图片卡片。")
                if prompt:
                    parts.append(f"提示词：{prompt}")
            elif key == "commute_plan_tool":
                parts.append(f"通勤规划：{val.get('origin_text', '')} → {val.get('destination_text', '')}")
                for route in val.get("routes", []):
                    if route.get("success"):
                        parts.append(f"- {route.get('label')}: {route.get('duration_text')}，{route.get('distance_text')}")
                    else:
                        parts.append(f"- {route.get('label', route.get('mode'))}: 规划失败，{route.get('error', '未知原因')}")
                if val.get("weather_reminder"):
                    parts.append(val["weather_reminder"])
            elif key == "nearby_service_tool":
                parts.append(f"周边服务：{val.get('center_name', '')} 附近的 {val.get('query', '')}")
                for item in val.get("items", [])[:10]:
                    distance = item.get("distance_meters")
                    distance_text = f"{distance} 米" if distance is not None else "距离暂不可用"
                    parts.append(f"- {item.get('name', '未命名地点')}：{distance_text}，{item.get('address', '')}")
            elif key == "email_tool" and val.get("status") == "awaiting_confirmation":
                preview = val.get("preview", {})
                parts.append(f"收件人: {preview.get('receiver', '')}")
                parts.append(f"主题: {preview.get('subject', '')}")
                parts.append(f"正文:\n{preview.get('body', '')}")
        elif key == "nearby_service_tool" and val.get("status") == "empty":
            parts.append(val.get("empty_message") or "指定范围内暂时没有找到相关地点，可以扩大范围或换个关键词。")
        else:
            # 工具执行失败，展示错误信息
            err = val.get("error", "未知错误")
            parts.append(f"「{key}」执行失败: {err}")
    return "\n".join(parts) if parts else "查询完成，但无结果返回。"
