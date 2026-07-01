"""Agent 服务编排层 — 串联意图分类 → 计划生成 → 执行 → 记忆保存"""
import json
import time
from collections.abc import Generator
from sqlalchemy.orm import Session

from agent_system.schemas.agent_request import AgentChatRequest
from agent_system.schemas.agent_response import AgentChatResponse
from agent_system.planner import classify_intent, build_plan
from agent_system.executor import run_plan, run_plan_stream
from agent_system.memory import get_or_create_session, get_history, refresh_summary_safely, save_message
from agent_system.middleware.middleware_graph import run_agent_middleware
from agent_system.supervisor import build_supervisor_decision
from DAO.agent_dao import create_task, update_task
from util.log import get_logger

logger = get_logger(__name__)


def _run_middleware(message: str, history: list | None = None) -> dict:
    """执行 LangGraph 中间件管线，返回统一结果 dict。"""
    return run_agent_middleware(message, history=history)


def _refresh_memory_after_reply(session_id: int, persona: str, db: Session) -> None:
    """回复保存后立即刷新会话摘要；失败不影响本次 Agent 回复。"""
    refresh_summary_safely(session_id=session_id, persona=persona, db=db)


def _task_status_from_tools(tool_calls: list[dict] | None, hitl_data: dict | None = None) -> str:
    """根据工具状态推导 AgentTask 状态，支持 partial_success/empty。"""
    if hitl_data:
        return "awaiting_hitl"
    if not tool_calls:
        return "success"
    statuses = [item.get("status") for item in tool_calls if isinstance(item, dict)]
    if statuses and all(status == "empty" for status in statuses):
        return "empty"
    if any(status == "partial_success" for status in statuses):
        return "partial_success"
    if statuses and all(status == "error" for status in statuses):
        return "error"
    if any(status == "error" for status in statuses):
        return "partial_success"
    return "success"


def _intent_from_middleware(metadata: dict) -> str:
    """从中间件 metadata 中推导业务意图，避免澄清任务全部写成通勤。"""
    if metadata.get("intent"):
        return metadata["intent"]
    if metadata.get("nearby"):
        return "nearby_service"
    if metadata.get("commute"):
        return "commute_plan"
    return "general_chat"


def _intent_override_from_middleware(metadata: dict, current_intent: str) -> str:
    """中间件已明确识别地图类意图时，优先使用确定性结果。"""
    middleware_intent = _intent_from_middleware(metadata)
    if middleware_intent in {"nearby_service", "commute_plan"}:
        return middleware_intent
    return current_intent


def _handle_clarification(
    session_id: int,
    user_id: str,
    persona: str,
    original_message: str,
    reply: str,
    metadata: dict,
    db: Session,
    t0: float,
) -> AgentChatResponse:
    """输入不完整时保存澄清回复，不进入 planner 和工具执行。"""
    intent = _intent_from_middleware(metadata)
    save_message(session_id, "user", original_message, db=db)
    task = create_task(
        db=db,
        user_id=user_id,
        persona=persona,
        intent=intent,
        original_message=original_message,
        session_id=session_id,
    )
    meta = {
        "intent": intent,
        "task_id": task.id,
        "clarification": True,
        "middleware": metadata,
    }
    save_message(session_id, "assistant", reply, metadata=meta, db=db)
    _refresh_memory_after_reply(session_id, persona, db)
    update_task(
        db,
        task.id,
        status="clarification",
        steps_json=json.dumps({"clarification": metadata}, ensure_ascii=False),
        total_duration_ms=int((time.time() - t0) * 1000),
    )
    return AgentChatResponse(
        reply=reply,
        intent=intent,
        persona=persona,
        tool_calls=None,
        sources=None,
        cards=None,
        session_id=session_id,
        task_id=task.id,
    )


def handle_agent_chat(
    req: AgentChatRequest,
    current_user: dict,
    db: Session,
    db_readonly: Session | None = None,
) -> dict:
    """同步版（向后兼容）"""
    t0 = time.time()

    # 0. 中间件管线
    session = get_or_create_session(user_id=current_user["username"], session_id=req.session_id, db=db)
    history = get_history(session.id, db)
    mw = _run_middleware(req.message, history=history)
    if mw["decision"] == "reject":
        return {"code": 400, "msg": mw["reason"], "data": None}
    if mw["decision"] == "clarification":
        result = _handle_clarification(
            session_id=session.id,
            user_id=current_user["username"],
            persona=req.persona,
            original_message=req.message,
            reply=mw["clarification"] or "请补充完整信息后再试。",
            metadata=mw.get("metadata") or {},
            db=db,
            t0=t0,
        )
        return {"code": 200, "msg": "ok", "data": result.model_dump(), "total": None}
    effective_message = mw["rewritten"] or req.message

    supervisor_decision = build_supervisor_decision(effective_message, persona=req.persona)
    if supervisor_decision:
        intent = supervisor_decision.intent
        plan = supervisor_decision.plan
    else:
        intent_result = classify_intent(effective_message)
        intent = _intent_override_from_middleware(mw.get("metadata") or {}, intent_result["intent"])
        plan = build_plan(message=effective_message, intent=intent, persona=req.persona, history=history)
    save_message(session.id, "user", req.message, db=db)

    # 创建 AgentTask 记录
    task = create_task(
        db=db, user_id=current_user["username"], persona=req.persona,
        intent=intent, original_message=req.message, session_id=session.id,
    )
    if mw["rewritten"]:
        update_task(db, task.id, rewritten_message=mw["rewritten"])

    result: AgentChatResponse = run_plan(
        plan=plan, user=current_user, db=db, db_readonly=db_readonly,
        student_no_override=req.student_no, original_message=req.message,
        session_id=session.id,
    )
    result.session_id = session.id
    result.task_id = task.id
    if supervisor_decision:
        result.supervisor = supervisor_decision.to_metadata()
    tool_meta = None
    if result.tool_calls:
        tool_meta = [{"tool_name": t.tool_name, "status": t.status, "summary": t.summary} for t in result.tool_calls]
    meta = {"intent": result.intent, "tool_calls": tool_meta, "task_id": task.id}
    if result.cards:
        meta["cards"] = result.cards
    if result.tool_monitoring:
        meta["tool_monitoring"] = result.tool_monitoring
    if supervisor_decision:
        meta["supervisor"] = supervisor_decision.to_metadata()
    save_message(
        session.id,
        "assistant",
        result.reply,
        metadata=meta,
        db=db,
    )
    _refresh_memory_after_reply(session.id, req.persona, db)

    # 更新 AgentTask
    update_task(db, task.id,
        status=_task_status_from_tools(tool_meta), plan_json=plan.model_dump_json(),
        steps_json=json.dumps({
            "tool_calls": tool_meta,
            "tool_monitoring": result.tool_monitoring,
            "cards": result.cards,
            "supervisor": supervisor_decision.to_metadata() if supervisor_decision else None,
        }, ensure_ascii=False),
        total_duration_ms=int((time.time() - t0) * 1000),
    )

    logger.info("Agent 处理完成: session=%s, intent=%s, reply_len=%s", session.id, intent, len(result.reply))
    return {"code": 200, "msg": "ok", "data": result.model_dump(), "total": None}


def handle_agent_chat_stream(
    req: AgentChatRequest,
    current_user: dict,
    db: Session,
    db_readonly: Session | None = None,
) -> Generator[str, None, None]:
    """
    流式版：逐步产出 SSE 事件字符串。

    SSE 事件类型：
      intent  — 识别到的意图
      session — 会话 ID
      plan    — 执行计划摘要
      tool_start / tool_end — 工具调用进度
      chunk   — LLM 生成的文本片段
      done    — 最终元数据（含 tool_calls、sources）
    """
    logger.info("Agent 流式请求: user=%s, message=%s", current_user["username"], req.message[:80])
    t0 = time.time()

    # 0. 中间件管线（先生成会话以获取历史）
    session = get_or_create_session(user_id=current_user["username"], session_id=req.session_id, db=db)
    history = get_history(session.id, db)

    mw = _run_middleware(req.message, history=history)
    if mw["decision"] == "reject":
        yield _sse("error", {"message": mw["reason"]})
        return
    yield _sse("guard_pass", {"status": "ok"})
    yield _sse("session", {"session_id": session.id})
    if mw["decision"] == "clarification":
        result = _handle_clarification(
            session_id=session.id,
            user_id=current_user["username"],
            persona=req.persona,
            original_message=req.message,
            reply=mw["clarification"] or "请补充完整信息后再试。",
            metadata=mw.get("metadata") or {},
            db=db,
            t0=t0,
        )
        yield _sse("intent", {"intent": result.intent, "confidence": 1.0})
        yield _sse("chunk", {"text": result.reply})
        yield _sse("done", {
            "intent": result.intent,
            "persona": result.persona,
            "tool_calls": None,
            "sources": None,
            "cards": None,
            "reply": result.reply,
            "task_id": result.task_id,
        })
        return
    effective_message = mw["rewritten"] or req.message
    if mw["rewritten"]:
        yield _sse("rewritten", {"original": req.message, "rewritten": mw["rewritten"]})

    # 1-3. Supervisor 路由优先识别明确跨域请求；未命中再走原单 Agent 意图分类。
    supervisor_decision = build_supervisor_decision(effective_message, persona=req.persona)
    if supervisor_decision:
        intent = supervisor_decision.intent
        logger.info("Supervisor 接管跨域请求: intent=%s, handoffs=%s", intent, len(supervisor_decision.handoffs))
        yield _sse("intent", {"intent": intent, "confidence": 1.0})
        yield _sse("supervisor", supervisor_decision.to_metadata())
    else:
        intent_result = classify_intent(effective_message)
        intent = _intent_override_from_middleware(mw.get("metadata") or {}, intent_result["intent"])
        logger.info("Agent 意图: %s (confidence=%.2f)", intent, intent_result["confidence"])
        yield _sse("intent", {"intent": intent, "confidence": intent_result["confidence"]})

    history = get_history(session.id, db)
    save_message(session.id, "user", req.message, db=db)

    # 4. 计划
    plan = (
        supervisor_decision.plan
        if supervisor_decision
        else build_plan(message=effective_message, intent=intent, persona=req.persona, history=history)
    )
    yield _sse("plan", {"intent": plan.intent, "steps": [s.tool_name for s in plan.steps], "need_llm_summary": plan.need_llm_summary})

    # 创建 AgentTask 记录
    task = create_task(
        db=db, user_id=current_user["username"], persona=req.persona,
        intent=intent, original_message=req.message, session_id=session.id,
    )
    if mw["rewritten"]:
        update_task(db, task.id, rewritten_message=mw["rewritten"])

    # 5. 流式执行 + 收集完整回复
    full_reply = ""
    tool_calls_data = None
    sources_data = None
    cards_data = None
    tool_monitoring_data = None
    hitl_data = None  # HITL 预览数据，需持久化以便历史消息回显
    hitl_step_id = None

    for event_str in run_plan_stream(
        plan=plan, user=current_user, db=db, db_readonly=db_readonly,
        student_no_override=req.student_no, original_message=req.message,
        session_id=session.id,
    ):
        # 捕获 HITL awaiting_confirmation 事件
        if event_str.startswith("event: awaiting_confirmation"):
            try:
                line = event_str.split("\n")[1]
                if line.startswith("data: "):
                    hitl_data = json.loads(line[6:])
                    hitl_step_id = hitl_data.get("step_id") or 1
            except (IndexError, json.JSONDecodeError):
                pass

        # 解析事件以收集元数据
        if event_str.startswith("event: chunk"):
            # 提取 chunk 文本
            try:
                line = event_str.split("\n")[1]
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    full_reply += chunk_data.get("text", "")
            except (IndexError, json.JSONDecodeError):
                pass

        elif event_str.startswith("event: done"):
            try:
                line = event_str.split("\n")[1]
                if line.startswith("data: "):
                    meta = json.loads(line[6:])
                    # 前端反馈按钮依赖 task_id，把本次 AgentTask 主键透传到 done 事件。
                    meta["task_id"] = task.id
                    if supervisor_decision:
                        meta["supervisor"] = supervisor_decision.to_metadata()
                    tool_calls_data = meta.get("tool_calls")
                    sources_data = meta.get("sources")
                    cards_data = meta.get("cards")
                    tool_monitoring_data = meta.get("tool_monitoring")
                    # executor 在 done 事件中直接携带完整回复，避免重复拼接
                    if meta.get("reply"):
                        full_reply = meta["reply"]
                    event_str = _sse("done", meta)
            except (IndexError, json.JSONDecodeError):
                pass

        yield event_str

    # 6. 保存 assistant 消息
    meta = {"intent": intent, "tool_calls": tool_calls_data, "task_id": task.id}
    if sources_data:
        meta["sources"] = sources_data
    if cards_data:
        meta["cards"] = cards_data
    if tool_monitoring_data:
        meta["tool_monitoring"] = tool_monitoring_data
    if supervisor_decision:
        meta["supervisor"] = supervisor_decision.to_metadata()
    if hitl_data:
        meta["hitl"] = {
            "tool_name": hitl_data.get("tool_name"),
            "step_id": hitl_step_id or hitl_data.get("step_id") or 1,
            "preview": hitl_data.get("preview", {}),
            "risk_level": hitl_data.get("risk_level"),
            "timeout_seconds": hitl_data.get("timeout_seconds"),
            "expires_at": hitl_data.get("expires_at"),
            "confirm_title": hitl_data.get("confirm_title"),
            "confirm_message": hitl_data.get("confirm_message"),
            "resolved": False,
        }
    saved_msg = save_message(
        session.id, "assistant", full_reply,
        metadata=meta,
        db=db,
    )
    _refresh_memory_after_reply(session.id, req.persona, db)

    # HITL 场景下，把消息 ID 注入执行状态以便 confirm 端点回写结果
    if hitl_data and saved_msg:
        from agent_system.hitl.hitl_manager import set_hitl_agent_task_id, set_hitl_message_id
        step_id = int(hitl_step_id or hitl_data.get("step_id") or 1)
        set_hitl_message_id(str(session.id), step_id, saved_msg.id)
        set_hitl_agent_task_id(str(session.id), step_id, task.id)

    # 更新 AgentTask
    update_task(db, task.id,
        status=_task_status_from_tools(tool_calls_data, hitl_data), plan_json=plan.model_dump_json(),
        steps_json=json.dumps({
            "tool_calls": tool_calls_data,
            "tool_monitoring": tool_monitoring_data,
            "cards": cards_data,
            "supervisor": supervisor_decision.to_metadata() if supervisor_decision else None,
        }, ensure_ascii=False),
        total_duration_ms=int((time.time() - t0) * 1000),
    )

    logger.info("Agent 流式完成: session=%s, intent=%s, reply_len=%s", session.id, intent, len(full_reply))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
