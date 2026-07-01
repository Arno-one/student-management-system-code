# 阶段 5 测试数据 — 记忆与执行

## 1. conversation_memory 测试

### 测试 1.1：创建新会话

```python
from agent_system.memory import get_or_create_session, get_history, save_message

# 前置: 数据库可用，用户 "test_user" 存在
session = get_or_create_session(user_id="test_user", session_id=None, db=db_session)
assert session is not None
assert session.user_id == "test_user"
assert session.session_title == "Agent 对话"
print(f"新会话: id={session.id}, title={session.session_title}")
```

### 测试 1.2：复用已有会话

```python
session2 = get_or_create_session(user_id="test_user", session_id=session.id, db=db_session)
assert session2.id == session.id  # 同一个会话
```

### 测试 1.3：保存和读取消息

```python
save_message(session.id, "user", "帮我查一下成绩", db=db_session)
save_message(
    session.id, "assistant", "你的数学成绩85分，语文90分！",
    metadata={"intent": "score_query", "tool_calls": [{"tool_name": "score_tool", "status": "success"}]},
    db=db_session,
)

history = get_history(session.id, db=db_session)
assert len(history) == 2
assert history[0]["role"] == "user"
assert history[0]["content"] == "帮我查一下成绩"
assert history[1]["role"] == "assistant"
assert "85" in history[1]["content"]
print(f"历史消息: {len(history)} 条")
```

### 测试 1.4：assistant 消息的 ai_content 结构化 JSON

```python
from DAO import talk_dao
msgs = talk_dao.get_messages_by_session(session.id, db_session)
assistant_msg = [m for m in msgs if m.role == "assistant"][0]
import json
data = json.loads(assistant_msg.ai_content)
assert "reply" in data
assert data["intent"] == "score_query"
assert len(data["tool_calls"]) == 1
print(f"结构化 JSON: {data}")
```

---

## 2. agent_executor 测试

### 测试 2.1：score_query 执行链（无真实 LLM，用 ollama 本地模型）

```python
from agent_system.schemas.task_state import ExecutionPlan, PlanStep
from agent_system.executor import run_plan

plan = ExecutionPlan(
    intent="score_query",
    persona="academic_mentor",
    steps=[PlanStep(step_id=1, tool_name="score_tool")],
    need_llm_summary=True,
    summary_instruction="用温和的语气告诉学生成绩情况",
)

# 前置: 当前用户 username 在 Student 表中有对应学号
user = {"id": 1, "username": "S2024001", "real_name": "测试学生"}
result = run_plan(
    plan=plan,
    user=user,
    db=db_session,
    original_message="帮我查一下成绩",
    provider="ollama",  # 用本地 ollama 避免消耗 API
)
assert result.intent == "score_query"
assert len(result.reply) > 10
assert len(result.tool_calls) == 1
assert result.tool_calls[0].tool_name == "score_tool"
print(f"回复: {result.reply}")
print(f"工具调用: {result.tool_calls}")
```

### 测试 2.2：emotional_support 执行链

```python
plan = ExecutionPlan(
    intent="emotional_support",
    persona="academic_mentor",
    steps=[],
    need_llm_summary=False,
    fallback_response="我能理解你的感受，考试确实让人紧张。",
)
result = run_plan(
    plan=plan,
    user=user,
    db=db_session,
    original_message="快要考试了好紧张",
    provider="ollama",
)
assert result.intent == "emotional_support"
assert len(result.reply) > 10
assert result.tool_calls is None  # 无工具调用
print(f"共情回复: {result.reply}")
```

### 测试 2.3：knowledge_qa 执行链

```python
plan = ExecutionPlan(
    intent="knowledge_qa",
    persona="academic_mentor",
    steps=[PlanStep(step_id=1, tool_name="rag_tool")],
    need_llm_summary=True,
    summary_instruction="结合检索到的知识内容回答用户问题",
)
result = run_plan(
    plan=plan,
    user=user,
    db=db_session,
    original_message="请假流程是什么",
    provider="ollama",
)
assert result.intent == "knowledge_qa"
assert len(result.tool_calls) == 1
assert result.tool_calls[0].tool_name == "rag_tool"
# sources 应该有值（如果 RAG 检索成功）
if result.sources:
    print(f"来源: {len(result.sources)} 条")
print(f"回复: {result.reply[:200]}")
```

### 测试 2.4：student_tool + score_tool 组合（academic_advice）

```python
plan = ExecutionPlan(
    intent="academic_advice",
    persona="academic_mentor",
    steps=[
        PlanStep(step_id=1, tool_name="student_tool"),
        PlanStep(step_id=2, tool_name="score_tool"),
    ],
    need_llm_summary=True,
    summary_instruction="结合学生成绩给出学业分析和改进建议",
)
result = run_plan(
    plan=plan,
    user=user,
    db=db_session,
    original_message="帮我分析一下这学期成绩",
    provider="ollama",
)
assert result.intent == "academic_advice"
# 应有 2 个工具调用记录（如果 student_tool 和 score_tool 都成功）
print(f"工具调用: {[(r.tool_name, r.status) for r in result.tool_calls]}")
print(f"回复: {result.reply[:200]}")
```

### 测试 2.5：工具调用失败时的降级

```python
plan = ExecutionPlan(
    intent="score_query",
    persona="academic_mentor",
    steps=[PlanStep(step_id=1, tool_name="score_tool")],
    need_llm_summary=True,
    summary_instruction="告诉学生成绩情况",
)
# 用一个不存在的学号触发工具失败
result = run_plan(
    plan=plan,
    user={"id": 1, "username": "NONEXISTENT", "real_name": "幽灵"},
    db=db_session,
    original_message="帮我查成绩",
    provider="ollama",
)
# 工具调用失败不应报错，回复应该降级
assert result.intent == "score_query"
assert result.tool_calls[0].status == "error"
assert len(result.reply) > 0
print(f"降级回复: {result.reply}")
```

### 测试 2.6：NL2SQL 执行链（需要 db_readonly）

```python
plan = ExecutionPlan(
    intent="data_query",
    persona="academic_mentor",
    steps=[PlanStep(step_id=1, tool_name="nl2sql_tool")],
    need_llm_summary=False,  # 数据直接展示
)
result = run_plan(
    plan=plan,
    user={"id": 1, "username": "admin", "real_name": "管理员"},
    db=db_session,
    db_readonly=db_readonly_session,
    original_message="统计学生总人数",
    provider="ollama",
)
assert result.intent == "data_query"
assert result.tool_calls[0].tool_name == "nl2sql_tool"
print(f"NL2SQL 结果: {result.reply[:300]}")
```

---

## 3. 完整链路：分类 → 计划 → 执行

```python
from agent_system.planner import classify_intent, build_plan
from agent_system.executor import run_plan
from agent_system.memory import get_or_create_session, save_message, get_history

def full_flow(message: str, user: dict):
    # 1. 意图分类
    intent_result = classify_intent(message)

    # 2. 生成计划
    plan = build_plan(message=message, intent=intent_result["intent"])

    # 3. 执行
    result = run_plan(
        plan=plan,
        user=user,
        db=db_session,
        original_message=message,
        provider="deepseek",
    )

    # 4. 保存记忆
    session = get_or_create_session(user["username"], None, db_session)
    save_message(session.id, "user", message, db=db_session)
    save_message(
        session.id, "assistant", result.reply,
        metadata={"intent": result.intent, "tool_calls": [
            {"tool_name": t.tool_name, "status": t.status}
            for t in (result.tool_calls or [])
        ]},
        db=db_session,
    )

    return result

# 测试 3 个场景
user = {"id": 1, "username": "S2024001", "real_name": "测试学生"}
print(full_flow("帮我查成绩", user).reply[:100])
print(full_flow("学校怎么请假", user).reply[:100])
print(full_flow("你好", user).reply[:100])
```

---

## 回归检查清单

- [ ] `get_or_create_session` 新建和复用均正确
- [ ] `save_message` 用户消息和 assistant 结构化 JSON 均持久化
- [ ] `get_history` 能正确提取 `reply` 字段
- [ ] 6 种意图的执行链均不报错
- [ ] 工具失败时降级回复非空
- [ ] 完整链路（分类→计划→执行→记忆）可跑通
