# 阶段 3 测试数据 — 规划层

## 1. 意图分类测试

### 测试 1.1：6 种意图分类

```python
from agent_system.planner import classify_intent

test_cases = [
    ("帮我查一下我的数学成绩", "score_query"),
    ("我数学多少分", "score_query"),
    ("这学期成绩有进步吗", "academic_advice"),
    ("怎么提高数学成绩", "academic_advice"),
    ("学校请假流程是什么", "knowledge_qa"),
    ("系统怎么查作业", "knowledge_qa"),
    ("3班有多少学生", "data_query"),
    ("哪些学生成绩超过90分", "data_query"),
    ("快要考试了好紧张", "emotional_support"),
    ("我压力好大不想学了", "emotional_support"),
    ("你好", "general_chat"),
    ("今天天气不错", "general_chat"),
]

ok = 0
for msg, expected in test_cases:
    result = classify_intent(msg)
    actual = result["intent"]
    match = actual == expected
    if match:
        ok += 1
    print(f"{'✓' if match else '✗'} | '{msg}' → {actual} (expected {expected})")

print(f"\n准确率: {ok}/{len(test_cases)}")
# 预期: >= 10/12 正确（general_chat 和 emotional_support 边界可能模糊）
```

### 测试 1.2：分类降级

```python
# 用 ollama 小模型可能导致 JSON 解析失败，验证降级逻辑
result = classify_intent("帮我查成绩", provider="ollama")
assert result["intent"] in ("score_query", "general_chat")  # ollama 可能解析失败降级
assert 0.0 <= result["confidence"] <= 1.0
```

---

## 2. 计划生成测试

### 测试 2.1：score_query 计划

```python
from agent_system.planner import build_plan

plan = build_plan(message="帮我查一下数学成绩", intent="score_query")
assert plan.intent == "score_query"
assert len(plan.steps) == 1
assert plan.steps[0].tool_name == "score_tool"
assert plan.need_llm_summary is True
assert plan.summary_instruction is not None
assert plan.fallback_response is None
print(f"plan: steps={plan.steps}, summary_instruction={plan.summary_instruction}")
```

### 测试 2.2：knowledge_qa 计划

```python
plan = build_plan(message="请假流程是什么", intent="knowledge_qa")
assert plan.intent == "knowledge_qa"
assert len(plan.steps) == 1
assert plan.steps[0].tool_name == "rag_tool"
assert plan.need_llm_summary is True
print(f"plan: steps={plan.steps}")
```

### 测试 2.3：emotional_support 计划（空步骤）

```python
plan = build_plan(message="考试压力好大", intent="emotional_support")
assert plan.intent == "emotional_support"
assert len(plan.steps) == 0
assert plan.need_llm_summary is False
assert plan.fallback_response is not None
assert len(plan.fallback_response) > 10
print(f"fallback_response: {plan.fallback_response}")
```

### 测试 2.4：academic_advice 计划

```python
plan = build_plan(message="我这学期数学怎么样", intent="academic_advice")
assert plan.intent == "academic_advice"
assert len(plan.steps) >= 1
assert plan.steps[0].tool_name == "score_tool"
assert plan.need_llm_summary is True
assert "成绩" in plan.summary_instruction or "分析" in plan.summary_instruction
print(f"plan: steps={[s.tool_name for s in plan.steps]}, instruction={plan.summary_instruction}")
```

### 测试 2.5：LLM 失败时的兜底计划

```python
# 用 ollama 小模型触发降级
plan = build_plan(message="帮我查成绩", intent="score_query", provider="ollama")
# 兜底计划也应有效
assert plan.intent == "score_query"
assert plan.steps[0].tool_name == "score_tool"
print(f"fallback plan used: steps={[s.tool_name for s in plan.steps]}")
```

### 测试 2.6：带对话历史的计划生成

```python
history = [
    {"role": "user", "content": "帮我查一下我的成绩"},
    {"role": "assistant", "content": "你的数学成绩是85分，语文90分。"},
]
plan = build_plan(
    message="那数学怎么样",
    intent="score_query",
    history=history
)
# 有历史时，LLM 可能根据上下文调整 plan，但核心结构不变
assert len(plan.steps) >= 1
print(f"plan with history: steps={[s.tool_name for s in plan.steps]}")
```

---

## 3. 完整链路：分类 → 计划

```python
from agent_system.planner import classify_intent, build_plan

def full_flow(message: str):
    intent_result = classify_intent(message)
    plan = build_plan(message=message, intent=intent_result["intent"])
    return {
        "message": message,
        "intent": intent_result["intent"],
        "confidence": intent_result["confidence"],
        "steps": [s.tool_name for s in plan.steps],
        "need_llm_summary": plan.need_llm_summary,
    }

# 测试 3 个典型场景
print(full_flow("帮我查成绩"))
# 预期: intent=score_query, steps=["score_tool"], need_llm_summary=True

print(full_flow("学校请假怎么请"))
# 预期: intent=knowledge_qa, steps=["rag_tool"], need_llm_summary=True

print(full_flow("你好"))
# 预期: intent=general_chat, steps=[], need_llm_summary=False
```

---

## 回归检查清单

- [ ] 6 种意图分类准确率 >= 80%
- [ ] 分类失败时降级到 general_chat
- [ ] 计划生成 LLM 失败时使用兜底计划
- [ ] emotional_support/general_chat 的 fallback_response 不为空
- [ ] 带历史对话的计划生成不报错
