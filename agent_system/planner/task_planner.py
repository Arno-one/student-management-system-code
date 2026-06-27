"""任务计划生成器 — 根据意图输出结构化执行计划"""
from llm_basic import structured_complete
from agent_system.prompts.planner_prompt import PLAN_BUILD_PROMPT, PlanSchema
from agent_system.schemas.task_state import ExecutionPlan, PlanStep
from util.log import get_logger

logger = get_logger(__name__)

# 各意图的硬编码兜底计划（LLM 失败时使用）
_FALLBACK_PLANS = {
    "score_query": ExecutionPlan(
        intent="score_query",
        steps=[PlanStep(step_id=1, tool_name="score_tool")],
        need_llm_summary=True,
        summary_instruction="用温和的语气告诉学生成绩情况",
    ),
    "academic_advice": ExecutionPlan(
        intent="academic_advice",
        steps=[PlanStep(step_id=1, tool_name="score_tool")],
        need_llm_summary=True,
        summary_instruction="结合学生的成绩数据，给出学业分析和改进建议，语气要温和鼓励",
    ),
    "knowledge_qa": ExecutionPlan(
        intent="knowledge_qa",
        steps=[PlanStep(step_id=1, tool_name="rag_tool")],
        need_llm_summary=True,
        summary_instruction="结合检索到的知识内容，用清晰易懂的方式回答用户问题",
    ),
    "data_query": ExecutionPlan(
        intent="data_query",
        steps=[PlanStep(step_id=1, tool_name="nl2sql_tool")],
        need_llm_summary=False,
    ),
    "emotional_support": ExecutionPlan(
        intent="emotional_support",
        steps=[],
        need_llm_summary=False,
        fallback_response="我理解你的感受。每个人都会有压力大的时候，这很正常。如果你愿意，可以和我聊聊是什么让你感到困扰。",
    ),
    "general_chat": ExecutionPlan(
        intent="general_chat",
        steps=[],
        need_llm_summary=False,
        fallback_response="你好！我是学业导师，有什么可以帮你的吗？",
    ),
    "weather_query": ExecutionPlan(
        intent="weather_query",
        steps=[PlanStep(step_id=1, tool_name="weather_tool")],
        need_llm_summary=True,
        summary_instruction="用友好的语气向用户播报天气情况",
    ),
    "email_draft": ExecutionPlan(
        intent="email_draft",
        steps=[PlanStep(step_id=1, tool_name="email_tool")],
        need_llm_summary=False,
    ),
}


def build_plan(
    message: str,
    intent: str,
    persona: str = "academic_mentor",
    history: list | None = None,
    provider: str = "deepseek",
) -> ExecutionPlan:
    """
    根据意图和上下文生成执行计划。

    Args:
        message: 用户原始消息
        intent: 已识别的意图
        persona: 角色标识
        history: 对话历史（可选），格式 [{"role": "user", "content": "..."}, ...]
        provider: LLM provider

    Returns:
        ExecutionPlan
    """
    # 构建历史摘要文本
    history_text = ""
    if history:
        recent = history[-6:]  # 最近 3 轮对话
        lines = []
        for h in recent:
            if h.get("role") == "user":
                role = "用户"
            elif h.get("role") == "summary":
                role = "摘要"
            else:
                role = "助手"
            content = str(h.get("content", ""))[:100]
            lines.append(f"{role}: {content}")
        history_text = "\n".join(lines)

    user_message = f"意图: {intent}\n用户消息: {message}"
    if history_text:
        user_message += f"\n\n对话历史:\n{history_text}"

    result = structured_complete(
        system_prompt=PLAN_BUILD_PROMPT,
        user_message=user_message,
        schema=PlanSchema,
        provider=provider,
    )

    if result["error"] or result["parsed"] is None:
        logger.warning("计划生成失败，使用兜底计划: intent=%s, error=%s", intent, result.get("error"))
        fallback = _FALLBACK_PLANS.get(intent, _FALLBACK_PLANS["general_chat"])
        fallback.persona = persona
        return fallback

    parsed = result["parsed"]

    # 转换 steps 列表
    steps = []
    for s in parsed.steps:
        if isinstance(s, dict):
            steps.append(PlanStep(
                step_id=s.get("step_id", len(steps) + 1),
                tool_name=s.get("tool_name", ""),
            ))

    plan = ExecutionPlan(
        intent=intent,
        persona=persona,
        steps=steps,
        need_llm_summary=parsed.need_llm_summary,
        summary_instruction=parsed.summary_instruction,
        fallback_response=parsed.fallback_response,
    )

    logger.info("计划生成: intent=%s, steps=%s, need_summary=%s",
                intent, [s.tool_name for s in steps], plan.need_llm_summary)
    return plan
