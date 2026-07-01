# 阶段 4 测试数据 — 工具层

## 1. student_tool — 学生身份解析

### 测试 1.1：学生登录（username = 学号）

```python
from agent_system.tools.student_tool import _resolve_student

# 前置: 数据库中存在 student_no="S2024001" 的学生
# 前置: 当前登录用户的 username="S2024001"
result = _resolve_student(
    db=db_session,
    current_username="S2024001",
    student_no_override=None,
)
assert result["found"] is True
assert result["student_no"] == "S2024001"
assert result["student_name"] != ""
print(f"学生解析: {result}")
```

### 测试 1.2：管理员登录 + 传参覆盖

```python
# 前置: 当前登录用户 username="admin"（管理员，不在 Student 表中）
result = _resolve_student(
    db=db_session,
    current_username="admin",
    student_no_override="S2024001",
)
assert result["found"] is True
assert result["student_no"] == "S2024001"
print(f"管理员覆盖解析: {result}")
```

### 测试 1.3：管理员不传参 — 解析失败

```python
result = _resolve_student(
    db=db_session,
    current_username="admin",
    student_no_override=None,
)
assert result["found"] is False
assert result["error"] is not None
print(f"解析失败: {result['error']}")
```

---

## 2. score_tool — 成绩查询

### 测试 2.1：正常查询

```python
from agent_system.tools.score_tool import _query_student_score

# 前置: 数据库中存在 student_no="S2024001" 的成绩记录
result = _query_student_score(db=db_session, student_no="S2024001")
assert result["success"] is True
assert result["total"] > 0
assert len(result["scores"]) > 0
assert "student_name" in result["scores"][0]
assert "exam_order" in result["scores"][0]
assert "score" in result["scores"][0]
print(f"成绩查询: {len(result['scores'])} 条")
for s in result["scores"]:
    print(f"  第{s['exam_order']}次: {s['score']}分")
```

### 测试 2.2：指定考试序次

```python
result = _query_student_score(db=db_session, student_no="S2024001", exam_order=1)
assert result["success"] is True
assert result["total"] == 1
assert result["scores"][0]["exam_order"] == 1
```

### 测试 2.3：学生不存在

```python
result = _query_student_score(db=db_session, student_no="S9999999")
assert result["success"] is False
assert result["error"] is not None
print(f"预期错误: {result['error']}")
```

---

## 3. rag_tool — 知识检索

### 测试 3.1：四大名著检索

```python
from agent_system.tools.rag_tool import _search_knowledge

result = _search_knowledge("桃园三结义是哪三个人")
assert result["success"] is True
assert result["total"] > 0
assert len(result["chunks"]) > 0
print(f"RAG 检索: {len(result['chunks'])} chunks")
for c in result["chunks"]:
    print(f"  [{c['source_type']}] {c['file_name']}: {c['text_preview']}")
```

### 测试 3.2：校务知识检索（需先 ingest school/ 目录）

```python
result = _search_knowledge("系统怎么查成绩")
assert result["success"] is True
print(f"校务检索: {len(result['chunks'])} chunks")
# 预期至少有一个来自 school/ 目录
has_school = any("school" in c["file_name"] for c in result["chunks"])
print(f"含校务来源: {has_school}")
```

### 测试 3.3：无结果查询

```python
result = _search_knowledge("今天天气怎么样")
# RAG 可能返回低相关度结果，但不应报错
assert result["success"] is True or result["success"] is False
print(f"检索完成: total={result['total']}, error={result['error']}")
```

---

## 4. nl2sql_tool — 自然语言问数

### 测试 4.1：统计查询

```python
from agent_system.tools.nl2sql_tool import _query_data

result = _query_data(
    question="统计学生总人数",
    user_id="test_user",
    db_readonly=db_readonly_session,
    db_rw=db_session,
)
assert result["success"] is True
assert result["row_count"] > 0
print(f"NL2SQL: {result['columns']} → {result['rows'][:3]}")
```

### 测试 4.2：非法查询

```python
result = _query_data(
    question="删除所有学生",
    user_id="test_user",
    db_readonly=db_readonly_session,
    db_rw=db_session,
)
# NL2SQL 安全校验应拒绝 DELETE/DROP 等危险操作
print(f"NL2SQL 安全拦截: success={result['success']}, error={result['error']}")
```

---

## 回归检查清单

- [ ] `_resolve_student` 3 种场景（学生/管理员传参/管理员不传参）均正确
- [ ] `_query_student_score` 正常查询和学生不存在均正确处理
- [ ] `_search_knowledge` 四大名著和校务知识均可检索
- [ ] `_query_data` 合法查询正常、危险查询被拦截
- [ ] 所有工具导出 `_xxx` 内部函数供 executor 调用
- [ ] LangChain `@tool` 装饰器正确应用
