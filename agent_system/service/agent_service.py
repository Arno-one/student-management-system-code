"""Agent 服务编排层 — 串联意图分类 → 计划生成 → 执行 → 记忆保存"""
import json
import time
from collections.abc import Generator
from sqlalchemy.orm import Session

from agent_system.schemas.agent_request import AgentChatRequest
from agent_system.schemas.agent_response import AgentChatResponse
from agent_system.planner import classify_intent, build_plan
from agent_system.executor import run_plan, run_plan_stream
from agent_system.memory import get_or_create_session, get_history, refresh_summary_if_needed, save_message
from agent_system.middleware.input_guard import check as guard_check
from agent_system.middleware.query_rewriter import check as rewrite_check
from agent_system.middleware.policy_checker import check as policy_check
from DAO.agent_dao import create_task, update_task
from util.log import get_logger

logger = get_logger(__name__)


def _run_middleware(message: str, history: list | None = None) -> dict:
    """执行中间件管线: guard → rewriter → policy，返回统一结果 dict"""
    # 1. 输入安全守卫
    guard = guard_check(message)
    if guard.decision == "reject":
        return {"decision": "reject", "reason": guard.reject_reason, "rewritten": None}

    # 2. 查询改写（需对话历史）
    rewrite = rewrite_check(message, history=history)
    rewritten = rewrite.rewritten_message

    # 3. 策略核验
    policy = policy_check(message, rewritten)
    if policy.decision == "reject":
        return {"decision": "reject", "reason": policy.reject_reason, "rewritten": rewritten}

    if policy.decision == "rewrite" and rewritten:
        return {"decision": "rewrite", "reason": None, "rewritten": rewritten}

    return {"decision": "pass", "reason": None, "rewritten": None}


def _refresh_memory_after_reply(session_id: int, persona: str, db: Session) -> None:
    """回复保存后刷新会话摘要；失败不影响本次 Agent 回复。"""
    refresh_summary_if_needed(session_id=session_id, persona=persona, db=db)


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
    effective_message = mw["rewritten"] or req.message

    intent_result = classify_intent(effective_message)
    intent = intent_result["intent"]
    save_message(session.id, "user", req.message, db=db)
    plan = build_plan(message=effective_message, intent=intent, persona=req.persona, history=history)

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
    tool_meta = None
    if result.tool_calls:
        tool_meta = [{"tool_name": t.tool_name, "status": t.status, "summary": t.summary} for t in result.tool_calls]
    meta = {"intent": result.intent, "tool_calls": tool_meta, "task_id": task.id}
    if result.cards:
        meta["cards"] = result.cards
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
        status="success", plan_json=plan.model_dump_json(),
        steps_json=json.dumps(tool_meta, ensure_ascii=False),
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
    effective_message = mw["rewritten"] or req.message
    if mw["rewritten"]:
        yield _sse("rewritten", {"original": req.message, "rewritten": mw["rewritten"]})

    # 1-3. 意图 → 会话 → 历史
    intent_result = classify_intent(effective_message)
    intent = intent_result["intent"]
    logger.info("Agent 意图: %s (confidence=%.2f)", intent, intent_result["confidence"])
    yield _sse("intent", {"intent": intent, "confidence": intent_result["confidence"]})

    yield _sse("session", {"session_id": session.id})

    history = get_history(session.id, db)
    save_message(session.id, "user", req.message, db=db)

    # 4. 计划
    plan = build_plan(message=effective_message, intent=intent, persona=req.persona, history=history)
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
    hitl_data = None  # HITL 预览数据，需持久化以便历史消息回显

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
                    tool_calls_data = meta.get("tool_calls")
                    sources_data = meta.get("sources")
                    cards_data = meta.get("cards")
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
    if hitl_data:
        meta["hitl"] = {
            "tool_name": hitl_data.get("tool_name"),
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
        set_hitl_message_id(str(session.id), 1, saved_msg.id)
        set_hitl_agent_task_id(str(session.id), 1, task.id)

    # 更新 AgentTask
    update_task(db, task.id,
        status="awaiting_hitl" if hitl_data else "success", plan_json=plan.model_dump_json(),
        steps_json=json.dumps(tool_calls_data, ensure_ascii=False),
        total_duration_ms=int((time.time() - t0) * 1000),
    )

    logger.info("Agent 流式完成: session=%s, intent=%s, reply_len=%s", session.id, intent, len(full_reply))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
