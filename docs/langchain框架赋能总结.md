# 学生管理系统 — LangChain 智能录入功能总结

## 一、项目背景

原有系统采用 **FastAPI + SQLAlchemy + Vue 3** 三层架构（API → Service → DAO），四个核心 CRUD 操作均为传统表单输入：

| 功能 | 端点 | 前端 View |
|------|------|-----------|
| 增加学生 | `POST /student/students` | `StudentView.vue` |
| 增加就业信息 | `POST /Employment/employment_create` | `EmploymentView.vue` |
| 增加成绩 | `POST /score/add` | `ScoreView.vue` |
| 修改学生信息 | `PATCH /student/students/{id}` | `StudentView.vue` |

项目中已有 `llm_basic.py` 封装了三个 LLM provider（DeepSeek / Qwen / Ollama）的 LangChain 实例，通过 `get_model(provider)` 工厂方法获取。但由于 DeepSeek API 不支持 `response_format`（JSON Schema 模式），不能直接使用 `with_structured_output()`。

---

## 二、方案设计

### 2.1 后端方案选型

| 方案 | 思路 | 风险 | 结论 |
|------|------|------|------|
| **A（选用）** 新增自然语言端点 | 不动原有端点，新增 `/extract` 端点接收 NL 文本，LLM 提取后复用现有 Service/DAO | 低，原有接口零影响 | 选用 |
| B 统一点 + 输入判断 | 改造原有端点同时接受 JSON 和文本 | 中，影响现有前端 | 不选 |
| C Agent 全接管 | LangChain Agent + @tool 包装 DAO | 高，Agent 不可控 | 不选 |

### 2.2 前端方案选型

| 方案 | 思路 | 结论 |
|------|------|------|
| **F1（选用）** 子标签页模式 | 每个 View 新增"智能录入"子标签 | 选用 |
| F2 表单内 AI 填充按钮 | 保留表单，弹出 AI 输入框回填 | 不选 |
| F3 全局入口 + 智能路由 | 侧边栏统一智能入口 | 不选 |

### 2.3 Grill-Me 详细决策复盘

以下记录了方案制定过程中逐项深入讨论的每个设计问题、备选方案以及最终决策理由。

---

**Q1: NL 端点的两段式交互**

> 用户输入自然语言 → 点"智能提取" → 看到预览 → 确认后才写入。这意味着后端需要两个端点还是端点？

| 选项 | 描述 | 评估 |
|------|------|------|
| 分离 | `POST /students/extract`（只做 LLM 提取，不写库）+ 复用现有 `POST /students`（确认后提交） | 提取和创建解耦，用户可在预览阶段修改字段再提交；后续可加"重新提取" |
| 合并 | `POST /students/nl` 既提取又创建 | 一步到位，但失去预览确认环节，LLM 提取错了直接脏数据入库 |

**决定：分离**。extract 端点 + 复用原有 create/update 端点。

---

**Q2: LLM 提取不完整时怎么办？**

> 用户说"新增学生张三，学号 S2024001"，没提班级 ID，但 `StudentCreate` 里 `class_id` 是必填的。

| 选项 | 描述 | 评估 |
|------|------|------|
| 返回缺失列表 | extract 端点返回尽力提取的结果 + `missing_required: ["class_id"]`，前端标红让用户手动补填 | LLM 职责是"辅助填表"而非"保证完整"，容错性好 |
| 多轮对话 | LLM 反问用户补全缺失字段 | 增加复杂度，不适合表单场景 |

**决定：返回缺失列表，前端标红。** `extract_service.py` 计算出 `missing_required`，SmartInput 组件把缺失字段的输入框标红并显示"（待补填）"。

---

**Q3: extract 端点的 LangChain 实现方式**

> `with_structured_output()` vs 手动 `JsonOutputParser`？

| 选项 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| `with_structured_output()` | `model.with_structured_output(StudentCreate)` | 代码少，LangChain 原生支持 | 底层调 `response_format`，DeepSeek 不支持 |
| 手动 Prompt + JSON 解析 | system prompt 注入 JSON 格式说明，`json.loads()` 手动解析 | 兼容所有 provider | 多写代码，需处理 JSON 解析失败 |

**决定：手动 Prompt + JSON 解析。** 因为 DeepSeek API 返回 `400: This response_format type is unavailable now`。但同时用 Pydantic `model_validate()` 做类型强转，保证数据质量。

---

**Q4: 需要一个独立的 Extract Schema**

> `StudentCreate` 有必填字段，但 extract 阶段所有字段都应该是 Optional 的。

**决定：每个实体创建独立的 Extract Schema**（全 Optional），与创建/修改的 Schema 分离：
- `StudentExtract` — 12 个全 Optional 字段，LLM 不编造缺失值
- `EmploymentExtract` — 7 个全 Optional 字段
- `ScoreExtract` — 3 个全 Optional 字段
- `StudentUpdateExtract` — 定位字段 + `changes: StudentChangeFields`

必填字段列表由调用方传入 `required_fields=["student_no", "class_id", "student_name"]`，不在 Schema 层面约束。

---

**Q5: extract 端点用哪个模型？**

| 维度 | 本地 Ollama (qwen2.5:3b) | 云端 DeepSeek (deepseek-chat) | 云端 Qwen (qwen-plus) |
|------|--------------------------|------------------------------|----------------------|
| 延迟 | 取决于本地 GPU | 通常 <1s | 通常 <1s |
| 成本 | 免费 | 每次几分钱 | 每次几分钱 |
| 准确性 | 3B 模型可能漏字段 | 稳定 | 稳定 |
| 一致性 | — | 项目中 nl2sql / work_service 已在使用 | 项目中未大量使用 |

**决定：默认 `deepseek`，`config.py` 加 `LLM_EXTRACT_PROVIDER` 可配置切换。** 不让前端实时传参切换 provider，避免过度灵活增加复杂度。

```python
# config.py
LLM_EXTRACT_PROVIDER = os.getenv("LLM_EXTRACT_PROVIDER", "deepseek")
```

---

**Q6: extract 端点的文件组织**

| 选项 | 描述 | 评估 |
|------|------|------|
| 按资源分文件 | `service/extract_service.py` 公共逻辑 + 各 API 文件加 extract 端点 | 符合项目现有的按资源分路由风格 |
| 统一点 | 一个 `/smart/extract` 端点，根据 `entity_type` 参数路由 Schema | 破坏现有风格，单一端点职责过重 |

**决定：按资源分文件。** 公共逻辑抽到 `service/extract_service.py`，四个 API 文件各自加 extract 端点调用公共服务。

---

**Q7: 前端组件复用**

> 三个 View 都要加智能录入子标签，结构几乎一样：textarea → 提取按钮 → 预览区 → 确认按钮。

**决定：抽取 `SmartInput.vue` 公共组件。** Props 包括 `extractUrl`、`submitUrl`、`submitMethod`、`fields`（字段定义列表）、`fieldMap`（预览字段→提交字段映射）。每个 View 只需声明式配置即可接入。

但"修改学生"不适用 SmartInput——因为它需要展示目标学生（只读）+ 变更字段（可编辑）的双层结构，因此单独实现自定义 UI。

---

**Q8: 修改学生信息的 NL 端点逻辑不同**

> 创建类操作只需提取实体字段，但"修改"需要先指定目标再描述变更。

**决定：`StudentUpdateExtract` Schema 区分"定位条件"和"变更字段"**：

```
StudentUpdateExtract {
  student_id: Optional[int]       // 直接指定 ID
  student_no: Optional[str]       // 或通过学号定位
  student_name: Optional[str]     // 辅助定位（防止改错人）
  changes: StudentChangeFields    // 实际要改的字段
}
```

如果用户只提供了学号没有 ID，后端在 extract 端点内自动调用 `student_dao.get_by_student_no()` 查库转换，前端不需要关心 ID。

---

**Q9: LLM 提取失败时的降级策略**

> API key 过期、网络超时、模型返回乱码 JSON 等情况如何处理？

| 场景 | 处理 |
|------|------|
| LLM 调用异常 | `extract_service.py` 统一 try-catch，返回 `{extracted: null, error: "具体原因", missing_required: [...]}` |
| 前端收到 error | 显示红色提示 + 完整空白预览表单让用户手动填，用户永远不会因为 LLM 挂了就不能操作 |
| 重试机制 | 前端提供"重新提取"按钮，仅在提取完成后显示，避免反复重试浪费 token |

**决定：失败降级到手动填写，而不是阻断用户操作。**

---

**Q10: extract 的 System Prompt 怎么设计**

> `with_structured_output()` 默认用 field name + description 传给 LLM，但 LLM 不懂中文业务语境。

**决定：每个 entity 维护一个定制的中文 system prompt**，包含：

- 每个字段的中文名称、格式说明、示例值
- 特殊规则（如 "N班" → `class_id=N`、"第N次考试" → `exam_order=N`）
- 约束（"用户没提到的字段不要编造"、"只输出 JSON 不输出其他文字"）

```python
# extract_service.py 示例片段
STUDENT_EXTRACT_PROMPT = """你是一个学生信息录入助手。从用户的自然语言描述中提取学生信息。

字段说明：
- student_no: 学号，如 "S2024001"
- class_id: 班级ID，数字。如果用户说"3班"意思是 class_id=3
- gender: 性别，"男"或"女"
...

规则：
1. 用户没提到的字段不要出现在 JSON 中，绝对不要编造值
2. "N班" 表示班级ID为N
3. 日期格式统一为 YYYY-MM-DD
4. 只输出 JSON，不要输出任何其他文字"""
```

四个实体各有独立的 prompt：`student` / `student_update` / `employment` / `score`。

---

**Q11: LLM 调用成本控制**

> extract 端点每次请求消耗 LLM token，反复提交或脚本刷会产生不必要的 API 费用。

| 措施 | 层级 | 说明 |
|------|------|------|
| RBAC 权限控制 | 服务端 | extract 端点加 `require_permission` 依赖，只有登录且有对应权限的用户能调用 |
| 前端防抖 | 客户端 | 提取按钮点击后 disabled 3 秒，防止用户狂点 |

**决定：两层轻量保护，不做服务端限流。** 内部管理系统用户量可控，过度设计没必要。

---

**Q12: 前端 `fields.value` 报错**

> SmartInput 组件的 `missingRequired` computed 中写了 `fields.value.filter(...)`，控制台报 `fields is not defined`。

**原因**：`fields` 是 Vue prop，在 `<script setup>` 中访问应写作 `props.fields`，不是 `fields.value`（它不是 ref）。

**决定：所有三处 `fields.value` 改为 `props.fields`。**

---

### 2.4 决策汇总表

| # | 决策点 | 选择 | 原因 |
|---|--------|------|------|
| 1 | 两端点 vs 端点 | 分离：`/extract` + 复用原端点 | 提取和创建解耦，用户可预览修改后再提交 |
| 2 | 缺失必填字段 | 返回 missing_required，前端标红 | LLM 职责是"辅助填表"而非"保证完整" |
| 3 | LLM Schema 策略 | 独立的 Extract Schema（全 Optional） | 与创建/修改的必填 Schema 分离，避免 LLM 编造值 |
| 4 | 模型选择 | 默认 deepseek，`config.py` 可配 | 与项目其他模块保持一致 |
| 5 | 代码组织 | `extract_service.py` 公共 + 各 API 独立端点 | 符合项目按资源分路由的风格 |
| 6 | 前端组件 | `SmartInput.vue` 公共组件 | 避免四个 View 复制四遍相同逻辑 |
| 7 | 修改 vs 创建 | 修改需要定位条件 + 变更字段双层提取 | 创建只需提取实体字段，修改需要知道改谁 |
| 8 | LLM 调用方式 | 手动 Prompt + JSON 解析 | DeepSeek 不支持 `response_format` |
| 9 | 类型转换 | Pydantic `model_validate()` | LLM 可能返回字符串 "3" 而非数字 3 |
| 10 | 失败降级 | error + 空白字段模板 | LLM 挂了用户依然能操作 |
| 11 | 成本控制 | RBAC + 前端 3 秒防抖 | 内部系统，轻度防护足够 |
| 12 | System Prompt | 每个 entity 维护中文 prompt | LLM 需要理解中文业务术语 |
| 13 | 修改定位 | 后端自动学号→ID 查库转换 | 前端不需要关心 ID，修改端点需要 ID |

---

## 三、新增文件与目录结构

```
项目根目录/
├── service/
│   └── extract_service.py          ← 新增：LLM 提取公共服务
├── scheme/
│   ├── student_scheme.py           ← 新增 StudentExtract / StudentUpdateExtract / StudentChangeFields
│   ├── employment_scheme.py        ← 新增 EmploymentExtract
│   └── schema_score.py             ← 新增 ScoreExtract
├── API/
│   ├── student_api.py              ← 新增 POST /students/extract + POST /students/update/extract
│   ├── employment_api.py           ← 新增 POST /employment_extract
│   └── score_api.py                ← 新增 POST /extract
├── config.py                       ← 新增 LLM_EXTRACT_PROVIDER 配置项
└── frontend-vue/src/
    ├── components/
    │   └── SmartInput.vue           ← 新增：智能录入公共组件
    └── views/
        ├── StudentView.vue          ← 新增"智能录入"+"智能修改"子标签
        ├── EmploymentView.vue       ← 新增"智能录入"子标签
        └── ScoreView.vue            ← 新增"智能录入"子标签
```

---

## 四、架构设计

### 4.1 请求流程

```
┌──────────┐   自然语言文本    ┌──────────────┐   LLM提取    ┌─────────────────┐
│  前端     │ ──────────────→ │ /extract 端点 │ ──────────→ │ extract_service  │
│SmartInput│                  │ (API层)       │             │ (Service层)      │
│  组件    │ ←── JSON(提取    │               │ ←── Pydantic│                 │
│  预览    │     结果+缺失)   │               │   Schema    │                 │
└────┬─────┘                  └──────────────┘             └─────────────────┘
     │ 用户确认
     │ POST/PATCH JSON
     ▼
┌──────────────┐   Service校验   ┌──────────────┐   DAO写库   ┌──────────────┐
│  原有端点     │ ─────────────→ │ 原有Service   │ ────────→ │ 原有DAO       │
│  (复用)      │                │               │            │              │
└──────────────┘                └──────────────┘            └──────────────┘
```

### 4.2 extract_service 公共逻辑

```
extract_fields(text, schema, entity, required_fields, provider)
    │
    ├─ 1. 根据 entity 选择中文 system prompt
    │     "student" / "student_update" / "employment" / "score"
    │
    ├─ 2. 基于 Pydantic schema 动态生成 JSON 格式说明
    │     { "student_no": string, "class_id": number, ... }
    │
    ├─ 3. 调用 get_model(provider).invoke([SystemMessage, HumanMessage])
    │
    ├─ 4. 清理 LLM 输出（去 ```json ... ``` 包裹）
    │
    ├─ 5. json.loads() 解析
    │
    ├─ 6. Pydantic model_validate() 类型强制转换（str→int/date）
    │
    ├─ 7. JSON 安全序列化（date → "YYYY-MM-DD"）
    │
    ├─ 8. 计算 missing_required（对照 required_fields 列表）
    │
    └─ 返回 {"extracted": {...}, "missing_required": [...], "error": null}
```

### 4.3 SmartInput 组件设计

```
Props:
  extractUrl      — 提取端点 URL
  submitUrl       — 提交端点 URL
  submitMethod    — POST / PATCH
  fields          — [{key, label, type, required, placeholder}]
  fieldMap        — {预览字段名: 提交字段名}

内部状态:
  text            — 用户输入的自然语言
  extracted       — 提取结果（可编辑）
  missingRequired — 缺失的必填字段列表（标红用）
  error           — 提取失败时的错误信息

流程:
  [输入] → [智能提取] → [预览(缺失标红)] → [确认提交] → [成功/失败]
```

### 4.4 修改学生 vs 创建的区别

创建学生（SmartInput 组件）：
```
NL输入 → POST /students/extract → {student_no, class_id, student_name, ...}
       → 预览 → POST /students/students → 创建成功
```

修改学生（独立 UI，不用 SmartInput）：
```
NL输入 → POST /students/update/extract → {student_id, student_no, student_name, changes: {...}}
        → 后端自动将学号转为 student_id →
        → 前端显示目标学生（只读）+ 可编辑变更字段 →
        → PATCH /student/students/{id} → 修改成功
```

---

## 五、四个功能端到端汇总

| # | 功能 | Extract 端点 | Submit 端点 | 前端组件 | Extract Schema |
|---|------|------------|------------|---------|---------------|
| 1 | 增加学生 | `POST /student/students/extract` | `POST /student/students` | SmartInput | StudentExtract |
| 2 | 增加就业 | `POST /Employment/employment_extract` | `POST /Employment/employment_create` | SmartInput | EmploymentExtract |
| 3 | 增加成绩 | `POST /score/extract` | `POST /score/add` | SmartInput | ScoreExtract |
| 4 | 修改学生 | `POST /student/students/update/extract` | `PATCH /student/students/{id}` | 自定义 UI | StudentUpdateExtract |

每个功能的必填字段：
- 学生：`student_no`, `class_id`, `student_name`（3 个）
- 就业：`student_no`, `student_name`, `class_id`（3 个）
- 成绩：`student_no`, `exam_order`, `score`（3 个）
- 修改：无必填（用户至少描述一个变更字段，否则无意义）

---

## 六、关键技术问题与解决方案

### 6.1 DeepSeek 不支持 response_format

**问题**：`model.with_structured_output(schema)` 底层调用 OpenAI 兼容的 `response_format: {type: "json_schema"}`，DeepSeek API 返回 400。

**解决**：改为在 system prompt 中注入 JSON 格式说明 + `json.loads()` 手动解析，兼容所有 LLM provider。

```python
# 旧方案（仅支持 OpenAI）
structured_model = model.with_structured_output(StudentExtract)
result = structured_model.invoke(messages)

# 新方案（通用）
system_prompt = base_prompt + "\n请严格按以下 JSON 格式输出：\n" + json_format
messages = [SystemMessage(content=system_prompt), HumanMessage(content=text)]
response = model.invoke(messages)
result = json.loads(clean_response(response.content))
```

### 6.2 LLM 返回字符串而非数字

**问题**：LLM 返回 `"class_id": "3"`（字符串）而非 `3`（整数），提交到后端 Pydantic 校验会失败。

**解决**：先 `json.loads()` 解析，再 `Pydantic model_validate()` 做类型强制转换（`"3"` → `3`，`"2025-07-01"` → `date`），最后手动做 JSON 安全序列化（`date` → `"2025-07-01"`）。

### 6.3 修改学生的定位问题

**问题**：前端修改端点 `PATCH /student/students/{id}` 需要 ID，但用户自然语言更可能说"把学号 S2025001 的专业改成..."，不会说 ID。

**解决**：`POST /student/students/update/extract` 端点自带 `db` 依赖，提取完成后如果只有学号没有 ID，自动调用 `student_dao.get_by_student_no()` 查库转换。

### 6.4 旧 Python 进程残留导致新代码未生效

**问题**：uvicorn 热重载有时不触发，且多次启动 `python main.py` 会创建多个进程同时绑定同一端口，旧进程响应请求。

**解决**：`cmd /c "taskkill /F /IM python.exe"` 杀干净所有 Python 进程后再重新启动。

### 6.5 SmartInput 根元素被 CSS 隐藏

**问题**：SmartInput 组件根元素写了 `class="card subcard"`，但 CSS 中 `.subcard { display: none }` 需要 `.show` 类覆盖，而组件内部没有 `.show`。

**解决**：去掉 SmartInput 的 `card subcard` 类（父级 div 已有），补充 `h3` 样式以替代 `.card h3` 的全局样式。

---

## 七、日志覆盖

遵循项目原有日志规范（`util/log.py`），在新增代码中补全了以下日志点：

| 文件 | 日志级别 | 记录内容 |
|------|---------|---------|
| `extract_service.py` | INFO | LLM 提取开始（entity / provider / text_len） |
| `extract_service.py` | DEBUG | LLM 原始返回（前 300 字符） |
| `extract_service.py` | WARNING | 提取结果缺失必填字段 |
| `extract_service.py` | ERROR | LLM 调用异常（含完整堆栈） |
| `extract_service.py` | WARNING | LLM 返回非标准 JSON |
| `student_api.py` | INFO/WARNING | 提取成功（字段数 + 缺失列表）/ 失败原因 |
| `student_api.py` | INFO/WARNING | 修改定位（学号→ID）/ 定位失败 |
| `employment_api.py` | INFO/WARNING | 提取成功 / 失败 |
| `score_api.py` | INFO/WARNING | 提取成功 / 失败 |

---

## 八、配置项

`.env` 或环境变量中可配置：

```bash
# LLM 提取服务使用的模型 provider（可选：deepseek / qwen / ollama）
LLM_EXTRACT_PROVIDER=deepseek
```

默认值为 `deepseek`，与项目中 `nl2sql_service.py`、`work_service.py` 保持一致。
