# 阶段 1 测试数据 — 基础设施

## 1. `llm_basic.structured_complete()` 测试

### 测试 1.1：正常解析简单 schema

```python
from pydantic import BaseModel, Field
from llm_basic import structured_complete

class TestIntent(BaseModel):
    intent: str = Field(description="意图分类结果")
    confidence: float = Field(description="置信度 0-1")

result = structured_complete(
    system_prompt="你是一个意图分类器。将用户消息分类为 score_query / knowledge_qa / general_chat。",
    user_message="帮我查一下我的数学成绩",
    schema=TestIntent,
    provider="deepseek"
)
# 预期: result["parsed"].intent == "score_query"
# 预期: result["parsed"].confidence >= 0.5
# 预期: result["error"] is None
assert result["parsed"] is not None
assert result["parsed"].intent in ("score_query", "knowledge_qa", "general_chat")
assert 0 <= result["parsed"].confidence <= 1
assert result["error"] is None
```

### 测试 1.2：带多个字段的复杂 schema

```python
class PlanStep(BaseModel):
    step_id: int = Field(description="步骤序号")
    tool_name: str = Field(description="工具名称")

class ExecutionPlan(BaseModel):
    intent: str = Field(description="用户意图")
    steps: list = Field(description="执行步骤列表", default_factory=list)
    need_llm_summary: bool = Field(description="是否需要LLM总结", default=False)

result = structured_complete(
    system_prompt="你是一个计划生成器。根据用户意图生成执行计划。",
    user_message="查询成绩：score_query",
    schema=ExecutionPlan,
    provider="deepseek"
)
# 预期: result["parsed"].intent == "score_query"
# 预期: result["parsed"].need_llm_summary 为 bool 类型
assert result["parsed"] is not None
assert result["error"] is None
```

### 测试 1.3：LLM 返回非法 JSON 时的错误处理

```python
# 用 ollama 小模型 + 一个 LLM 不理解的 schema 来触发 JSON 解析错误
result = structured_complete(
    system_prompt="输出一段散文，不要输出 JSON。",
    user_message="写一首诗",
    schema=TestIntent,
    provider="ollama"  # 小模型更容易出错
)
# 预期: 如果解析失败，parsed 为 None，error 不为空
# 如果碰巧解析成功，那是运气好，不是 bug
print(f"parsed={result['parsed']}, error={result['error']}")
```

---

## 2. `RAG/retrieval_service.search_context()` 测试

### 测试 2.1：四大名著检索

```python
from RAG.retrieval_service import search_context

result = search_context("桃园三结义是哪三个人", enable_rerank=True)

# 预期: 返回至少 1 个相关片段
assert len(result.chunks) > 0
# 预期: 改写查询不为空
assert len(result.rewritten_query) > 0
# 预期: 片段文件名包含三国
file_names = [c.file_name for c in result.chunks]
assert any("三国" in f for f in file_names), f"文件名不含三国: {file_names}"
```

### 测试 2.2：校务知识库检索（需先执行 ingest 导入）

```python
result = search_context("请假流程是什么", enable_rerank=True)

# 预期: 返回校务相关片段
assert len(result.chunks) > 0
file_names = [c.file_name for c in result.chunks]
print(f"检索到 {len(result.chunks)} 个片段: {file_names}")
# 至少有一个来自 school/ 目录
assert any("school" in f for f in file_names), f"无校务来源: {file_names}"
```

### 测试 2.3：关闭精排

```python
result = search_context("孙悟空", enable_rerank=False)
assert result.rerank_enabled == False
assert len(result.chunks) > 0
```

---

## 3. `RAG/controller.py` `/ask` 接口测试

### 测试 3.1：接口返回格式不变

```bash
curl -X POST http://127.0.0.1:8088/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "桃园三结义是哪三个人", "enable_rerank": true}'
```

预期响应:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "question": "桃园三结义是哪三个人",
    "rewritten_query": "...",
    "answer": "...",
    "citations": [...],
    "trace": {
      "rewrite_ms": 0,
      "candidate_count": 3,
      "final_count": 3,
      "prompt_ms": 0,
      "context_tokens": 0,
      "context_blocks": 0,
      "generate_ms": 0,
      "total_ms": 0,
      "fallback": false
    }
  },
  "total": null
}
```

---

## 4. `service/extract_service.extract_fields()` 测试

### 测试 4.1：学生提取（与改动前行为一致）

```bash
curl -X POST http://127.0.0.1:8088/student/students_extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"text": "新增学生张三，学号S2024001，班级3班，男，20岁，计算机专业本科"}'
```

预期: 返回 `student_no: "S2024001"`, `student_name: "张三"`, `class_id: 3` 等

### 测试 4.2：成绩提取

```bash
curl -X POST http://127.0.0.1:8088/score/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"text": "学生S2025001第1次考试成绩85分"}'
```

预期: 返回 `student_no: "S2025001"`, `exam_order: 1`, `score: 85`

---

## 回归检查清单

- [ ] `POST /rag/ask` 四大名著问答正常
- [ ] `POST /student/students_extract` NL 提取正常
- [ ] `POST /score/extract` NL 提取正常
- [ ] `POST /Employment/employment_extract` NL 提取正常
- [ ] `POST /rag/ingest` 入库正常（含新 school/ 目录）
- [ ] 日志中不再有 `_log_candidates` 的调用
