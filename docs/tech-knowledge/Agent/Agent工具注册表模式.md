# Agent 工具注册表模式

## 为什么需要它

当 Agent 需要调用越来越多工具时，会面临：

1. **硬编码分发**：`if tool_name == "weather": ... elif tool_name == "score": ...`，每加一个工具要改执行器代码
2. **参数传递混乱**：每个工具的入参不同，执行器需要知道每个工具的特定参数名
3. **上游依赖处理**：工具 B 需要工具 A 的结果作为输入，如何自动传递？
4. **缓存策略不一致**：有些工具结果可以缓存（成绩查询），有些不能（邮件发送）

工具注册表模式解决：**让执行器用统一方式发现、调用、缓存工具，新增工具只需注册一个类。**

适用场景：
- Agent 平台（可插拔工具生态）
- 工作流引擎（通用任务执行器）
- 任何需要动态注册和调用工具的框架

---

## 本项目中的应用

本项目实现了基于 `BaseTool` 抽象类 + `_TOOL_REGISTRY` 注册表 + `ToolContext` 上下文的工具调用体系。

| 组件 | 作用 |
|------|------|
| `BaseTool` | 抽象基类，定义 `name`, `description`, `inputs_schema`, `run(ctx)` |
| `ToolContext` | 统一参数容器：params + upstream_results + user + db sessions |
| `_TOOL_REGISTRY` | 工具名 → 工具实例的映射表 |
| `_CACHEABLE_TOOLS` | 声明哪些工具结果可缓存 |
| `inputs_from` | PlanStep 间的依赖声明，执行器自动提取上游字段 |

---

## 实现流程

```mermaid
flowchart TD
    A[ExecutionPlan] --> B[遍历 PlanStep]
    B --> C{step.tool_name 在 _TOOL_REGISTRY?}
    C -->|否| D[跳过, 记录 error]
    C -->|是| E[_build_tool_context]

    E --> F[填充 params: 从 step.params 复制]
    E --> G[处理 inputs_from: 从上游结果按 inputs_schema 匹配字段]
    E --> H[注入默认值: student_no, username, user_id]
    E --> I[注入 NL 参数: question/prompt/request_text 未填则用原始消息]

    I --> J[构建 ToolContext]
    J --> K{tool_name 在 _CACHEABLE_TOOLS?}
    K -->|是| L{缓存命中?}
    L -->|是| M[返回缓存结果, 标记 _cached=true]
    L -->|否| N[tool.run(ctx)]
    K -->|否| N

    N --> O[结果存入 executed dict]
    O --> P[写入 session 缓存]
    P --> Q[检测 HITL: status == awaiting_confirmation?]
```

---

## 核心实现

### 1. 工具基类

```python
# agent_system/tools/base.py
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

@dataclass
class ToolContext:
    """执行器在调用工具前填充的上下文"""
    params: dict = field(default_factory=dict)          # 工具参数
    upstream_results: dict[str, dict] = field(default_factory=dict)  # 上游工具结果
    user: dict = field(default_factory=dict)             # 当前用户
    db: Session | None = None                            # 读写数据库
    db_readonly: Session | None = None                   # 只读数据库

class BaseTool:
    """所有工具必须继承并实现 run()"""
    name: str = ""
    description: str = ""
    inputs_schema: dict[str, type] = {}   # 声明工具接受的参数名

    def run(self, ctx: ToolContext) -> dict:
        raise NotImplementedError
```

### 2. 注册表

```python
# agent_system/executor/agent_executor.py
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

# 读操作工具（幂等，可缓存）
_CACHEABLE_TOOLS = {"score_tool", "student_tool", "rag_tool"}
```

### 3. 通用工具执行（无硬编码 if/elif）

```python
def _execute_step(step, tool, ctx: ToolContext, user: dict) -> dict:
    if step.tool_name == "student_tool":
        return _resolve_student(...)  # 唯一例外：身份解析
    return tool.run(ctx)  # 通用分发
```

### 4. 上游依赖自动注入

```python
def _build_tool_context(step, user, db, db_readonly, executed, student_no):
    params = dict(step.params) if step.params else {}

    # 从 inputs_from 引用的上游结果中按字段名匹配
    for upstream_name in (step.inputs_from or []):
        upstream_result = executed.get(upstream_name, {})
        if upstream_result:
            tool = _TOOL_REGISTRY.get(step.tool_name)
            if tool and hasattr(tool, "inputs_schema"):
                for field_name in tool.inputs_schema:
                    if field_name not in params and field_name in upstream_result:
                        params[field_name] = upstream_result[field_name]
    # ...
    return ToolContext(params=params, upstream_results=executed, ...)
```

### 5. Session 级缓存

```python
def _cache_key_for(tool_name: str, ctx: ToolContext) -> str:
    params_str = json.dumps(ctx.params, ensure_ascii=False, sort_keys=True)
    return f"{tool_name}:{params_str}"

# 读操作工具在同一个 session 内相同参数不重复调用
if step.tool_name in _CACHEABLE_TOOLS:
    cached = _cache_get(sid, cache_key)
    if cached is not None:
        result = cached
        result["_cached"] = True
    else:
        result = _execute_step(step, tool, ctx, user)
        _cache_set(sid, cache_key, result)
```

---

## 最佳实践

### 应该这样设计
- **`inputs_schema` 声明参数**：每个工具声明自己接受哪些字段，执行器据此自动匹配上游结果
- **读操作缓存**：幂等的查询工具结果在 session 内缓存，相同参数不重复调用
- **`ToolContext` 统一入参**：所有工具接收同一个上下文对象，而不是零散的参数列表
- **`run()` 返回 dict**：所有工具返回统一结构 `{success, data, error, ...}`，执行器做通用处理

### 不应该这样设计
- 不要在执行器中硬编码 `if tool_name == "xxx": do_xxx()` —— 新增工具必须改写执行器
- 不要让工具直接访问数据库（应通过 `ctx.db` 注入，方便测试 mock）
- 不要让工具感知执行器的调度逻辑（工具只管 `run(ctx)`，不管被谁调用）

### 常见踩坑
- **inputs_schema 不声明会导致上游结果无法注入**：如果 Tool B 依赖 Tool A 的结果，B 必须声明对应字段名
- **缓存 key 必须包含完整参数**：`_cache_key_for` 用 `sort_keys=True` 的 JSON 做指纹，避免参数顺序影响

---

## 面试亮点

**面试官可能追问：**
> "如果新增一个工具，需要改几处代码？"

回答：两处。一是创建工具类继承 `BaseTool` 并实现 `run()`，二是在 `_TOOL_REGISTRY` 注册。如果是读操作且需缓存，在 `_CACHEABLE_TOOLS` 加一行。执行器代码不需要改。

> "为什么不直接用 LangChain 的 Tool？"

回答：LangChain Tool 更适合单轮调用场景。我们的工具有 `inputs_from` 跨步骤依赖、session 级缓存、HITL 暂停恢复、统一 `ToolContext` 注入数据库连接等需求，自定义基类更灵活。

---

## 可以迁移到哪些项目

- Agent 平台（通用工具插件体系）
- 工作流引擎（任务步骤执行器）
- RPA 自动化（动作注册与执行）
- AI 助手（技能插件系统）
- MCP 客户端（工具发现与调用）

---

## 标签

#Agent #工具注册表 #设计模式 #插件化 #BaseTool
