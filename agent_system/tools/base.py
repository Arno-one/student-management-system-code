"""Agent 工具基类 — 定义统一工具接口和调用上下文"""
from dataclasses import dataclass, field
from sqlalchemy.orm import Session


@dataclass
class ToolContext:
    """工具执行上下文，executor 在调用工具前填充"""
    params: dict = field(default_factory=dict)
    upstream_results: dict[str, dict] = field(default_factory=dict)
    user: dict = field(default_factory=dict)
    db: Session | None = None
    db_readonly: Session | None = None


class BaseTool:
    """Agent 工具基类，所有工具需继承并实现 run()"""

    name: str = ""
    description: str = ""
    inputs_schema: dict[str, type] = {}

    def run(self, ctx: ToolContext) -> dict:
        raise NotImplementedError
