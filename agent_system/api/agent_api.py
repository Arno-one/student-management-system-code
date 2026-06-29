"""Agent API 路由"""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from database import get_db, get_db_readonly
from util.rbac import get_current_user, require_role
from util.log import get_logger
from scheme.response_scheme import success

from agent_system.schemas.agent_request import AgentChatRequest
from agent_system.service.agent_service import handle_agent_chat, handle_agent_chat_stream
from agent_system.memory import get_history
from agent_system.prompts.persona_prompt import PERSONA_REGISTRY
from agent_system.hitl.hitl_schema import HitlConfirmRequest
from agent_system.hitl.hitl_manager import get_paused_state, clear_paused_state
from agent_system.tools.email_whitelist import ALLOWED_RECIPIENTS
from agent_system.tools.mcp_client import tencent_map_mcp_client
from DAO.agent_dao import (
    create_feedback,
    get_admin_tasks,
    get_feedback_by_task_tool,
    get_feedbacks_by_task_ids,
    get_task_by_id,
    update_task,
)

logger = get_logger(__name__)

agent_router = APIRouter()


class AgentFeedbackRequest(BaseModel):
    """Agent 任务级反馈请求"""
    task_id: int = Field(..., description="关联的 AgentTask ID")
    rating: int = Field(..., ge=1, le=5, description="评分，1=差评，5=好评")
    comment: str | None = Field(None, max_length=1000, description="用户补充评价")
    tool_name: str | None = Field(None, max_length=50, description="预留步骤级反馈字段")


def _clamp_days(days: int) -> int:
    """监控时间窗口限制在 1-30 天，避免一次拉取过多任务"""
    return max(1, min(days or 7, 30))


def _percentile(values: list[int], percent: float) -> int:
    """计算简单百分位，样本为空时返回 0"""
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return int(ordered[0])
    idx = round((len(ordered) - 1) * percent)
    return int(ordered[idx])


def _rate(numerator: int, denominator: int) -> float:
    """返回百分比，保留 2 位小数"""
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def _parse_tool_calls(raw: str | None) -> list[dict]:
    """从 AgentTask.steps_json 中解析工具调用记录"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("tool_calls"), list):
        return [item for item in data["tool_calls"] if isinstance(item, dict)]
    return []


def _parse_steps_payload(raw: str | None) -> dict:
    """解析 AgentTask.steps_json，兼容旧版直接存 tool_calls 列表的格式。"""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"tool_calls": [item for item in data if isinstance(item, dict)]}
    return {}


def _parse_tool_monitoring(raw: str | None) -> dict:
    """读取工具轻量监控字段，主要用于地图 provider、兜底和结果数量统计。"""
    payload = _parse_steps_payload(raw)
    monitoring = payload.get("tool_monitoring")
    return monitoring if isinstance(monitoring, dict) else {}


def _parse_cards(raw: str | None) -> list[dict]:
    """读取结构化卡片摘要；旧任务没有 cards 时返回空列表。"""
    payload = _parse_steps_payload(raw)
    cards = payload.get("cards")
    return [item for item in cards if isinstance(item, dict)] if isinstance(cards, list) else []


def _provider_summary(monitoring: dict) -> str:
    """把 provider 监控压成表格可读摘要。"""
    parts = []
    for tool_name, item in monitoring.items():
        if not isinstance(item, dict):
            continue
        provider = item.get("provider") or "unknown"
        fallback = "，兜底" if item.get("fallback_used") else ""
        result_count = item.get("result_count")
        count_text = f"，{result_count}条" if result_count is not None else ""
        parts.append(f"{tool_name}: {provider}{fallback}{count_text}")
    return "；".join(parts)


def _card_summary(cards: list[dict]) -> str:
    """把卡片类型压成摘要，便于监控表快速定位卡片产出。"""
    if not cards:
        return ""
    bucket: dict[str, int] = {}
    for card in cards:
        key = str(card.get("type") or "unknown")
        bucket[key] = bucket.get(key, 0) + 1
    return "；".join(f"{key}×{count}" for key, count in bucket.items())


_NEGATIVE_REASON_KEYWORDS = [
    ("地图定位", ["定位", "地址", "经纬度", "宝安", "龙岗", "地图", "路线"]),
    ("结果为空", ["没有", "未查到", "空", "查不到", "无结果"]),
    ("答案错误", ["错", "错误", "不对", "不准确", "乱说"]),
    ("工具失败", ["失败", "异常", "报错", "不能用", "不可用"]),
    ("响应慢", ["慢", "卡", "等太久", "超时"]),
    ("体验问题", ["不好用", "看不懂", "啰嗦", "格式", "排版"]),
]


def _negative_reason_label(comment: str | None) -> str:
    """用轻量关键词把差评原因归类，不做复杂 NLP，避免误判成本过高。"""
    text = (comment or "").strip()
    if not text:
        return "未填写原因"
    for label, keywords in _NEGATIVE_REASON_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return label
    return "其他"


def _task_to_admin_row(task, feedback_map: dict[int, object]) -> dict:
    """把 AgentTask 转成前端监控表格需要的扁平结构"""
    feedback = feedback_map.get(task.id)
    tool_calls = _parse_tool_calls(task.steps_json)
    monitoring = _parse_tool_monitoring(task.steps_json)
    cards = _parse_cards(task.steps_json)
    return {
        "id": task.id,
        "create_time": task.create_time.isoformat() if task.create_time else None,
        "user_id": task.user_id,
        "persona": task.persona,
        "intent": task.intent,
        "status": task.status,
        "total_duration_ms": task.total_duration_ms or 0,
        "tool_calls": tool_calls,
        "tool_monitoring": monitoring,
        "cards": cards,
        "tool_summary": "；".join(
            f"{item.get('tool_name', '-')}: {item.get('status', '-')}"
            for item in tool_calls
        ),
        "provider_summary": _provider_summary(monitoring),
        "card_summary": _card_summary(cards),
        "feedback_rating": feedback.rating if feedback else None,
        "feedback_comment": feedback.comment if feedback else None,
        "original_message": (task.original_message or "")[:120],
    }


def _load_monitor_context(
    db: Session,
    days: int,
    status: str | None = None,
    intent: str | None = None,
    limit: int | None = None,
) -> tuple[list, dict[int, object], int]:
    """统一加载监控任务和反馈，减少各端点重复查询"""
    window_days = _clamp_days(days)
    since = datetime.now() - timedelta(days=window_days)
    tasks = get_admin_tasks(db, since=since, status=status, intent=intent, limit=limit)
    feedbacks = get_feedbacks_by_task_ids(db, [task.id for task in tasks])
    # 任务级反馈优先，若后续存在步骤级反馈，这里仍取每个 task 第一条用于列表展示。
    feedback_map = {}
    for item in feedbacks:
        feedback_map.setdefault(item.task_id, item)
    return tasks, feedback_map, window_days


@agent_router.post("/chat/stream", summary="Agent 聊天（SSE 流式）")
def chat_stream(
    req: AgentChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    db_readonly: Session = Depends(get_db_readonly),
):
    """
    向 Agent 发送消息，通过 SSE 流式返回结果。

    事件类型：
    - intent:  {"intent": "score_query", "confidence": 0.9}
    - session: {"session_id": 1}
    - plan:    {"intent": "...", "steps": [...], "need_llm_summary": true}
    - tool_start: {"tool_name": "score_tool"}
    - tool_end:   {"tool_name": "score_tool", "status": "success", "summary": "查询到3条成绩"}
    - chunk:   {"text": "..."}
    - done:    {"intent": "...", "tool_calls": [...], "sources": [...]}
    """
    logger.info("Agent SSE 流式请求: user=%s, message=%s", current_user["username"], req.message[:80])
    return StreamingResponse(
        handle_agent_chat_stream(req=req, current_user=current_user, db=db, db_readonly=db_readonly),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@agent_router.post("/chat", summary="Agent 主聊天入口（同步）")
def chat(
    req: AgentChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    db_readonly: Session = Depends(get_db_readonly),
):
    """同步版 Agent 聊天（向后兼容）"""
    logger.info("Agent 聊天请求: user=%s, message=%s", current_user["username"], req.message[:80])
    result = handle_agent_chat(req=req, current_user=current_user, db=db, db_readonly=db_readonly)
    return result


@agent_router.get("/sessions", summary="获取当前用户的 Agent 会话列表")
def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from DAO import talk_dao
    user_id = current_user["username"]
    logger.info("获取 Agent 会话列表: user=%s", user_id)
    sessions = talk_dao.get_sessions_by_user(user_id, db)
    result = []
    for s in sessions:
        result.append({
            "id": s.id, "title": s.session_title, "summary": s.summary,
            "update_time": s.update_time.isoformat() if s.update_time else None,
            "create_time": s.create_time.isoformat() if s.create_time else None,
        })
    return success(result)


@agent_router.get("/sessions/{session_id}/messages", summary="获取指定会话的历史消息")
def get_messages(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from DAO import talk_dao
    import json
    session = talk_dao.get_session_by_id(session_id, db)
    if not session or session.user_id != current_user["username"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    logger.info("获取 Agent 会话消息: session=%s, user=%s", session_id, current_user["username"])
    msgs = talk_dao.get_messages_by_session(session_id, db)
    task_ids = []
    result = []
    for m in msgs:
        item = {
            "id": m.id, "role": m.role,
            "content": m.user_content if m.role == "user" else None,
            "reply": None, "metadata": None,
            "create_time": m.create_time.isoformat() if m.create_time else None,
        }
        if m.role == "assistant" and m.ai_content:
            try:
                data = json.loads(m.ai_content)
                item["reply"] = data.get("reply", m.ai_content)
                item["metadata"] = {k: v for k, v in data.items() if k != "reply"}
                task_id = item["metadata"].get("task_id") if item["metadata"] else None
                if task_id:
                    try:
                        task_ids.append(int(task_id))
                    except (TypeError, ValueError):
                        pass
            except (json.JSONDecodeError, TypeError):
                item["reply"] = m.ai_content
        result.append(item)

    feedback_map = {}
    for feedback in get_feedbacks_by_task_ids(db, task_ids):
        # v2.2 仍以任务级反馈为主；工具级反馈后续扩展时单独处理。
        if feedback.tool_name is None:
            feedback_map[feedback.task_id] = feedback

    for item in result:
        metadata = item.get("metadata") or {}
        try:
            task_id = int(metadata.get("task_id")) if metadata.get("task_id") else None
        except (TypeError, ValueError):
            task_id = None
        feedback = feedback_map.get(task_id)
        if feedback:
            metadata["feedback"] = {
                "submitted": True,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "tool_name": feedback.tool_name,
                "feedback_id": feedback.id,
            }
            item["metadata"] = metadata
    return success(result)


@agent_router.get("/personas", summary="获取可用的 Agent 角色列表")
def list_personas():
    personas = []
    for key, entry in PERSONA_REGISTRY.items():
        personas.append({
            "id": key,
            "name": entry["name"],
            "icon": entry.get("icon", ""),
            "description": entry["description"],
        })
    return success(personas)


@agent_router.post("/feedback", summary="提交 Agent 任务反馈")
def submit_feedback(
    req: AgentFeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交或覆盖当前用户对某次 Agent 任务的反馈"""
    task = get_task_by_id(db, req.task_id)
    if not task or task.user_id != current_user["username"]:
        raise HTTPException(status_code=404, detail="Agent 任务不存在或无权反馈")

    # v2.2 约定：同一轮任务反馈只能提交一次，历史回放也必须保持锁定。
    tool_name = req.tool_name.strip() if req.tool_name else None
    comment = req.comment.strip() if req.comment else None
    existing = get_feedback_by_task_tool(db, task_id=req.task_id, tool_name=tool_name)
    if existing:
        raise HTTPException(status_code=409, detail="本轮对话已经提交过反馈，不能重复提交")

    fb = create_feedback(
        db=db,
        task_id=req.task_id,
        rating=req.rating,
        comment=comment,
        tool_name=tool_name,
    )
    logger.info(
        "Agent 反馈已提交: user=%s, task=%s, rating=%s, updated=%s",
        current_user["username"],
        req.task_id,
        req.rating,
        False,
    )
    return success({
        "feedback_id": fb.id,
        "task_id": fb.task_id,
        "rating": fb.rating,
        "comment": fb.comment,
        "tool_name": fb.tool_name,
        "updated": False,
    })


@agent_router.get("/admin/metrics", summary="Agent 监控总览指标")
def admin_metrics(
    days: int = 7,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """管理员查看 Agent 近 N 天总览指标"""
    tasks, feedback_map, window_days = _load_monitor_context(db, days=days)
    total = len(tasks)
    success_count = sum(1 for task in tasks if task.status == "success")
    partial_success_count = sum(1 for task in tasks if task.status == "partial_success")
    clarification_count = sum(1 for task in tasks if task.status == "clarification")
    empty_count = sum(1 for task in tasks if task.status == "empty")
    error_count = sum(1 for task in tasks if task.status == "error")
    cancelled_count = sum(1 for task in tasks if task.status == "cancelled")
    awaiting_count = sum(1 for task in tasks if task.status == "awaiting_hitl")
    running_count = sum(1 for task in tasks if task.status in {"running", "pending"})
    completed_total = success_count + partial_success_count + empty_count + error_count
    durations = [task.total_duration_ms or 0 for task in tasks if task.total_duration_ms]

    feedbacks = list(feedback_map.values())
    positive = sum(1 for item in feedbacks if item.rating >= 4)
    negative = sum(1 for item in feedbacks if item.rating <= 2)

    return success({
        "window_days": window_days,
        "total_tasks": total,
        "completed_tasks": completed_total,
        "success_count": success_count,
        "partial_success_count": partial_success_count,
        "clarification_count": clarification_count,
        "empty_count": empty_count,
        "error_count": error_count,
        "cancelled_count": cancelled_count,
        "awaiting_hitl_count": awaiting_count,
        "running_count": running_count,
        "success_rate": _rate(success_count + partial_success_count, completed_total),
        "avg_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
        "p50_duration_ms": _percentile(durations, 0.5),
        "p99_duration_ms": _percentile(durations, 0.99),
        "feedback_count": len(feedbacks),
        "positive_feedback_count": positive,
        "negative_feedback_count": negative,
        "positive_rate": _rate(positive, len(feedbacks)),
        "negative_rate": _rate(negative, len(feedbacks)),
    })


@agent_router.get("/admin/mcp/tencent-map/health", summary="腾讯地图 MCP 健康状态")
def admin_tencent_map_mcp_health(
    _: dict = Depends(require_role("admin")),
):
    """管理员查看腾讯地图 MCP 底座状态，便于判断是否启用增强链路。"""
    return success(tencent_map_mcp_client.health())


@agent_router.get("/admin/metrics/timeseries", summary="Agent 每日调用趋势")
def admin_metrics_timeseries(
    days: int = 7,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """按日期统计调用量、失败量和平均耗时"""
    tasks, _, window_days = _load_monitor_context(db, days=days)
    today = datetime.now().date()
    date_keys = [(today - timedelta(days=offset)).isoformat() for offset in range(window_days - 1, -1, -1)]
    bucket = {key: {"date": key, "total": 0, "error": 0, "avg_duration_ms": 0, "_durations": []} for key in date_keys}

    for task in tasks:
        if not task.create_time:
            continue
        key = task.create_time.date().isoformat()
        if key not in bucket:
            continue
        bucket[key]["total"] += 1
        if task.status == "error":
            bucket[key]["error"] += 1
        if task.total_duration_ms:
            bucket[key]["_durations"].append(task.total_duration_ms)

    rows = []
    for key in date_keys:
        item = bucket[key]
        durations = item.pop("_durations")
        item["avg_duration_ms"] = int(sum(durations) / len(durations)) if durations else 0
        rows.append(item)
    return success(rows)


@agent_router.get("/admin/metrics/intents", summary="Agent 意图分布指标")
def admin_metrics_intents(
    days: int = 7,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """按意图统计调用量和耗时"""
    tasks, _, _ = _load_monitor_context(db, days=days)
    bucket: dict[str, dict] = {}
    for task in tasks:
        key = task.intent or "unknown"
        item = bucket.setdefault(key, {"intent": key, "count": 0, "success": 0, "error": 0, "_durations": []})
        item["count"] += 1
        if task.status in {"success", "partial_success"}:
            item["success"] += 1
        elif task.status == "error":
            item["error"] += 1
        if task.total_duration_ms:
            item["_durations"].append(task.total_duration_ms)

    rows = []
    for item in bucket.values():
        durations = item.pop("_durations")
        item["avg_duration_ms"] = int(sum(durations) / len(durations)) if durations else 0
        item["p50_duration_ms"] = _percentile(durations, 0.5)
        item["p99_duration_ms"] = _percentile(durations, 0.99)
        rows.append(item)
    rows.sort(key=lambda row: row["count"], reverse=True)
    return success(rows)


@agent_router.get("/admin/metrics/tools", summary="Agent 工具失败率指标")
def admin_metrics_tools(
    days: int = 7,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """从 steps_json/tool_calls 中解析各工具调用和失败率"""
    tasks, _, _ = _load_monitor_context(db, days=days)
    bucket: dict[str, dict] = {}
    for task in tasks:
        for call in _parse_tool_calls(task.steps_json):
            key = call.get("tool_name") or "unknown_tool"
            item = bucket.setdefault(key, {
                "tool_name": key,
                "total": 0,
                "success": 0,
                "partial_success": 0,
                "empty": 0,
                "clarification": 0,
                "error": 0,
            })
            item["total"] += 1
            status = call.get("status")
            if status == "success":
                item["success"] += 1
            elif status == "partial_success":
                item["partial_success"] += 1
            elif status == "empty":
                item["empty"] += 1
            elif status == "clarification":
                item["clarification"] += 1
            elif status == "error":
                item["error"] += 1

    rows = []
    for item in bucket.values():
        item["failure_rate"] = _rate(item["error"], item["total"])
        rows.append(item)
    rows.sort(key=lambda row: (row["failure_rate"], row["total"]), reverse=True)
    return success(rows)


@agent_router.get("/admin/metrics/providers", summary="Agent 地图 provider 分布指标")
def admin_metrics_providers(
    days: int = 7,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """从 tool_monitoring 中聚合 provider、兜底次数、空结果和错误情况。"""
    tasks, _, _ = _load_monitor_context(db, days=days)
    bucket: dict[str, dict] = {}
    for task in tasks:
        monitoring = _parse_tool_monitoring(task.steps_json)
        for tool_name, raw_item in monitoring.items():
            if not isinstance(raw_item, dict):
                continue
            provider = raw_item.get("provider") or "unknown_provider"
            key = f"{tool_name}:{provider}"
            item = bucket.setdefault(key, {
                "tool_name": tool_name,
                "provider": provider,
                "total": 0,
                "success": 0,
                "partial_success": 0,
                "empty": 0,
                "error": 0,
                "fallback_count": 0,
                "result_count": 0,
                "last_error_code": "",
                "last_error_message": "",
            })
            status = raw_item.get("status") or "unknown"
            item["total"] += 1
            if status in {"success", "partial_success", "empty", "error"}:
                item[status] += 1
            if raw_item.get("fallback_used"):
                item["fallback_count"] += 1
            try:
                item["result_count"] += int(raw_item.get("result_count") or 0)
            except (TypeError, ValueError):
                pass
            if raw_item.get("error_code") or raw_item.get("error_message"):
                item["last_error_code"] = raw_item.get("error_code") or ""
                item["last_error_message"] = raw_item.get("error_message") or ""

    rows = []
    for item in bucket.values():
        item["fallback_rate"] = _rate(item["fallback_count"], item["total"])
        item["empty_rate"] = _rate(item["empty"], item["total"])
        item["failure_rate"] = _rate(item["error"], item["total"])
        rows.append(item)
    rows.sort(key=lambda row: (row["failure_rate"], row["fallback_rate"], row["total"]), reverse=True)
    return success(rows)


@agent_router.get("/admin/metrics/feedback-reasons", summary="Agent 差评原因聚合")
def admin_metrics_feedback_reasons(
    days: int = 7,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """对 1-2 分反馈做轻量关键词归因，帮助管理员快速定位高频问题。"""
    tasks, feedback_map, _ = _load_monitor_context(db, days=days)
    task_by_id = {task.id: task for task in tasks}
    bucket: dict[str, dict] = {}
    for feedback in feedback_map.values():
        if feedback.rating > 2:
            continue
        label = _negative_reason_label(feedback.comment)
        item = bucket.setdefault(label, {"reason": label, "count": 0, "examples": []})
        item["count"] += 1
        task = task_by_id.get(feedback.task_id)
        if len(item["examples"]) < 3:
            item["examples"].append({
                "task_id": feedback.task_id,
                "intent": task.intent if task else "",
                "comment": feedback.comment or "",
                "message": (task.original_message or "")[:80] if task else "",
            })

    rows = list(bucket.values())
    rows.sort(key=lambda row: row["count"], reverse=True)
    return success(rows)


@agent_router.get("/admin/tasks", summary="Agent 最近任务列表")
def admin_tasks(
    days: int = 7,
    status: str | None = None,
    intent: str | None = None,
    limit: int = 50,
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """最近 Agent 任务列表，供管理员排查具体问题"""
    safe_limit = max(1, min(limit or 50, 200))
    tasks, feedback_map, _ = _load_monitor_context(
        db,
        days=days,
        status=status or None,
        intent=intent or None,
        limit=safe_limit,
    )
    return success([_task_to_admin_row(task, feedback_map) for task in tasks])


@agent_router.post("/step/confirm", summary="HITL 步骤确认（邮件发送等需要人工确认的操作）")
def confirm_step(
    req: HitlConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    用户在收到 awaiting_confirmation 事件后，调用此端点确认或取消。
    - confirmed=true: 执行实际操作
    - confirmed=false: 取消操作
    """
    state = get_paused_state(req.task_id, req.step_id)
    if state is None:
        raise HTTPException(status_code=404, detail="待确认的步骤不存在或已超时，请重新发起任务")

    # 更新关联的 TalkMessage
    def _update_message(result_status: str, result_msg: str):
        if not state.message_id:
            return
        from DAO.talk_dao import get_message_by_id
        import json as _json
        msg = get_message_by_id(state.message_id, db)
        if msg and msg.ai_content:
            try:
                data = _json.loads(msg.ai_content)
                if "hitl" in data:
                    data["hitl"]["resolved"] = True
                    data["hitl"]["resultStatus"] = result_status
                    data["hitl"]["resultMsg"] = result_msg
                msg.ai_content = _json.dumps(data, ensure_ascii=False)
                db.commit()
                logger.info("HITL 消息已更新: msg_id=%s, status=%s", state.message_id, result_status)
            except (_json.JSONDecodeError, TypeError) as e:
                logger.warning("HITL 消息更新 JSON 解析失败: msg_id=%s, %s", state.message_id, e)

    if not req.confirmed:
        _update_message("cancelled", "已取消操作")
        if state.agent_task_id:
            update_task(db, state.agent_task_id, status="cancelled")
        clear_paused_state(req.task_id, req.step_id)
        logger.info("HITL 用户取消: task=%s, step=%s", req.task_id, req.step_id)
        return success({"status": "cancelled", "message": "操作已取消"})

    if state.tool_name != "email_tool":
        clear_paused_state(req.task_id, req.step_id)
        if state.agent_task_id:
            update_task(db, state.agent_task_id, status="error")
        raise HTTPException(status_code=400, detail=f"暂不支持确认执行工具: {state.tool_name}")

    # v2.1 首个规则化场景仍是邮件发送，后续高风险工具可在此按 tool_name 扩展执行器。
    preview = state.preview
    subject = preview.get("subject", "")
    body = preview.get("body", "")
    receiver = preview.get("receiver", "")

    # 用户可能修改了邮件内容
    if req.modified_params:
        subject = req.modified_params.get("subject", subject)
        body = req.modified_params.get("body", body)
        receiver = req.modified_params.get("receiver", receiver)

    # 二次白名单校验
    if receiver not in ALLOWED_RECIPIENTS:
        _update_message("err", f"收件人 {receiver} 不在白名单内")
        clear_paused_state(req.task_id, req.step_id)
        if state.agent_task_id:
            update_task(db, state.agent_task_id, status="error")
        raise HTTPException(status_code=400, detail=f"收件人 {receiver} 不在白名单内")

    from util.email import send_email
    result = send_email(subject, body, receiver)
    clear_paused_state(req.task_id, req.step_id)

    if result.get("success"):
        logger.info("HITL 邮件已发送: receiver=%s, subject=%s", receiver, subject[:40])
        _update_message("ok", result.get("message", "邮件已发送"))
        if state.agent_task_id:
            update_task(db, state.agent_task_id, status="success")
        return success({"status": "sent", "message": result.get("message", "邮件已发送")})
    else:
        logger.error("HITL 邮件发送失败: %s", result.get("message"))
        _update_message("err", result.get("message", "邮件发送失败"))
        if state.agent_task_id:
            update_task(db, state.agent_task_id, status="error")
        raise HTTPException(status_code=500, detail=result.get("message", "邮件发送失败"))
