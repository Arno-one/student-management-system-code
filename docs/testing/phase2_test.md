# 阶段 2 测试数据 — Agent 数据结构

## 1. Schema 字段校验

### 测试 1.1：AgentChatRequest 基础校验

```python
from agent_system.schemas import AgentChatRequest

# 正常请求
req = AgentChatRequest(message="帮我查一下成绩")
assert req.message == "帮我查一下成绩"
assert req.persona == "academic_mentor"  # 默认值
assert req.session_id is None
assert req.student_no is None

# 带学号请求
req2 = AgentChatRequest(message="查成绩", student_no="S2024001")
assert req2.student_no == "S2024001"

# 空消息应拒绝
try:
    AgentChatRequest(message="")
    assert False, "应该抛出 ValidationError"
except Exception:
    pass  # 预期行为
```

### 测试 1.2：AgentChatResponse 构建

```python
from agent_system.schemas import AgentChatResponse, ToolCallRecord

resp = AgentChatResponse(
    reply="你的数学成绩是85分，表现不错！",
    intent="score_query",
    tool_calls=[ToolCallRecord(tool_name="score_tool", status="success", summary="查询到1条成绩记录")],
    session_id=1
)
assert resp.intent == "score_query"
assert len(resp.tool_calls) == 1
assert resp.tool_calls[0].tool_name == "score_tool"
```

### 测试 1.3：ExecutionPlan 构建

```python
from agent_system.schemas import ExecutionPlan, PlanStep

# score_query 场景
plan = ExecutionPlan(
    intent="score_query",
    steps=[PlanStep(step_id=1, tool_name="score_tool")],
    need_llm_summary=True,
    summary_instruction="用温和的语气告诉学生成绩情况"
)
assert len(plan.steps) == 1
assert plan.need_llm_summary is True

# emotional_support 场景（无步骤）
plan2 = ExecutionPlan(
    intent="emotional_support",
    steps=[],
    need_llm_summary=False,
    fallback_response="我能理解你的感受，考试确实会让人紧张。先深呼吸，你已经很努力了。"
)
assert len(plan2.steps) == 0
assert plan2.fallback_response is not None
```

---

## 2. Prompt 模板完整性

### 测试 2.1：意图分类 prompt 的结构化输出

```python
from llm_basic import structured_complete
from agent_system.prompts import INTENT_CLASSIFY_PROMPT, IntentResult

test_cases = [
    ("帮我查一下我的数学成绩", "score_query"),
    ("我最近成绩怎么样，有没有进步", "academic_advice"),
    ("学校请假流程是什么", "knowledge_qa"),
    ("3班有多少学生", "data_query"),
    ("快要考试了好紧张", "emotional_support"),
    ("你好，今天天气不错", "general_chat"),
]

for msg, expected in test_cases:
    result = structured_complete(
        system_prompt=INTENT_CLASSIFY_PROMPT,
        user_message=msg,
        schema=IntentResult,
        provider="deepseek"
    )
    actual = result["parsed"].intent
    match = "✓" if actual == expected else f"✗ (expected {expected})"
    print(f"{match} | '{msg}' → {actual}")
```

预期：6 个用例中至少 5 个分类正确（`general_chat` 边界最模糊，允许偶尔偏差）。

### 测试 2.2：计划生成的 schema 校验

```python
from llm_basic import structured_complete
from agent_system.prompts import PLAN_BUILD_PROMPT, PlanSchema

result = structured_complete(
    system_prompt=PLAN_BUILD_PROMPT,
    user_message="意图: score_query, 消息: 帮我查一下成绩",
    schema=PlanSchema,
    provider="deepseek"
)
plan = result["parsed"]
assert plan.intent == "score_query"
assert len(plan.steps) == 1
assert plan.steps[0]["tool_name"] == "score_tool"
assert plan.need_llm_summary is True
assert plan.summary_instruction is not None
assert plan.fallback_response is None
```

### 测试 2.3：Persona 注册表

```python
from agent_system.prompts import PERSONA_REGISTRY

assert "academic_mentor" in PERSONA_REGISTRY
persona = PERSONA_REGISTRY["academic_mentor"]
assert persona["name"] == "学业导师"
assert "温和" in persona["description"]
assert len(persona["system_prompt"]) > 50
```

---

## 回归检查清单

- [ ] `AgentChatRequest` 默认值正确
- [ ] `ExecutionPlan` 支持空 steps（emotional_support/general_chat）
- [ ] 意图分类 6 类 prompt 正确注入
- [ ] 计划生成 prompt 按规则输出 `need_llm_summary` 和 `fallback_response`
