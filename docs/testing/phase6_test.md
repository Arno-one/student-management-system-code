# 阶段 6 测试数据 — 入口层

## 1. 接口联调测试

### 测试 1.1：POST /agent/chat — 成绩查询

```bash
# 前置: 已登录，拿到 Bearer token
# 前置: 数据库中学生 S2024001 有成绩记录

curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "message": "帮我查一下我的成绩",
    "persona": "academic_mentor"
  }'
```

预期响应格式:
```json
{
  "code": 200,
  "msg": "ok",
  "data": {
    "reply": "...(自然语言成绩报告)...",
    "intent": "score_query",
    "persona": "academic_mentor",
    "tool_calls": [
      {"tool_name": "score_tool", "status": "success", "summary": "查询到 N 条成绩记录"}
    ],
    "sources": null,
    "session_id": 1
  },
  "total": null
}
```

### 测试 1.2：POST /agent/chat — 知识问答

```bash
curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "message": "系统怎么查成绩",
    "persona": "academic_mentor"
  }'
```

预期: intent=knowledge_qa, tool_calls 含 rag_tool, sources 不为空

### 测试 1.3：POST /agent/chat — 情绪陪伴

```bash
curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "快要考试了好紧张"}'
```

预期: intent=emotional_support, tool_calls=null, reply 含共情语气

### 测试 1.4：POST /agent/chat — 多轮追问

```bash
# 第一轮
curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "帮我查一下成绩"}'
# 记录返回的 session_id，假设为 5

# 第二轮：带 session_id 追问
curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "那数学这门课怎么样", "session_id": 5}'
```

预期: 第二轮返回的 session_id 仍是 5，且 Agent 能理解"数学这门课"指成绩

### 测试 1.5：POST /agent/chat — 管理员指定学号

```bash
# admin 登录后查指定学生的成绩
curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "message": "查成绩",
    "student_no": "S2024001"
  }'
```

### 测试 1.6：参数校验 — 空消息

```bash
curl -X POST http://127.0.0.1:8088/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": ""}'
```

预期: HTTP 422（参数校验失败）

---

## 2. 会话管理接口测试

### 测试 2.1：GET /agent/sessions

```bash
curl http://127.0.0.1:8088/agent/sessions \
  -H "Authorization: Bearer <token>"
```

预期:
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {"id": 1, "title": "Agent 对话", "summary": null, ...}
  ],
  "total": 1
}
```

### 测试 2.2：GET /agent/sessions/{id}/messages

```bash
curl http://127.0.0.1:8088/agent/sessions/1/messages \
  -H "Authorization: Bearer <token>"
```

预期: 返回 user 和 assistant 消息列表，assistant 消息有 `reply` 和 `metadata` 字段

### 测试 2.3：GET /agent/sessions/{id}/messages — 会话不存在

```bash
curl http://127.0.0.1:8088/agent/sessions/99999/messages \
  -H "Authorization: Bearer <token>"
```

预期: HTTP 404

### 测试 2.4：GET /agent/personas

```bash
curl http://127.0.0.1:8088/agent/personas \
  -H "Authorization: Bearer <token>"
```

预期:
```json
{
  "code": 200,
  "data": [
    {"id": "academic_mentor", "name": "学业导师", "description": "..."}
  ]
}
```

---

## 3. Swagger UI 验证

启动服务后访问 `http://127.0.0.1:8088/docs`，确认：
- [ ] 出现新的 "智能Agent" 标签分组
- [ ] POST /agent/chat 可展开查看参数 schema
- [ ] GET /agent/sessions 可展开
- [ ] GET /agent/sessions/{session_id}/messages 可展开
- [ ] GET /agent/personas 可展开
- [ ] 所有接口的 Authorization 头可正常输入 Bearer token

---

## 4. 回归检查清单

- [ ] 各接口均需 Bearer token（未登录返回 401）
- [ ] 1.1-1.5 的正常场景均返回 code=200
- [ ] 1.6 参数校验返回 422
- [ ] 2.1-2.4 会话管理接口正常
- [ ] 多轮追问 session_id 正确延续
- [ ] 管理员传 student_no 能查到指定学生
- [ ] Swagger UI 中 Agent 分组独立展示
