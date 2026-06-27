"""任务计划与执行状态"""
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: int = Field(..., description="步骤序号")
    tool_name: str = Field(..., description="工具名称")
    params: dict = Field(default_factory=dict, description="显式传入参数")
    inputs_from: list[str] = Field(default_factory=list, description="依赖的前序步骤 tool_name 列表，executor 自动从上游结果中按字段名匹配参数")


class ExecutionPlan(BaseModel):
    intent: str = Field(..., description="用户意图")
    persona: str = Field("academic_mentor", description="角色标识")
    steps: list[PlanStep] = Field(default_factory=list, description="按顺序执行的步骤")
    need_llm_summary: bool = Field(False, description="工具结果是否需要 LLM 二次总结")
    summary_instruction: str | None = Field(None, description="LLM 总结时的指令")
    fallback_response: str | None = Field(None, description="不走工具时的直接回复内容")
