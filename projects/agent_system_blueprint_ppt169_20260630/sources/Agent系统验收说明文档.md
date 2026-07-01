# Agent 系统验收说明文档

> 本文档对照《二阶段项目需求文档》对 Agent 子系统进行逐项验收，覆盖功能需求、非功能需求、架构演进、测试验证与交付文档清单。

---

## 零、验收结论摘要

本次验收结论可以先直接给出：

- **结论一：需求文档列出的 21 项验收条目全部通过。**
- **结论二：系统不仅完成了基础功能，还在反馈闭环、监控观测、地图 MCP、HITL 规则化、监控性能优化和 UI 自动回归上形成了超额交付。**
- **结论三：当前 Agent 子系统已具备“可运行、可维护、可扩展、可观测、可回归”的工程化落地能力。**

为避免文档表述与实际实现脱节，本文统一按当前代码口径描述：

- 11 类意图
- 8 个工具
- 3 个 Persona
- 3 类结构化卡片
- 1 套 HITL 规则化确认机制
- 1 个腾讯地图 MCP 能力底座
- 1 个 Supervisor 多 Agent 最小闭环

---

## 一、验收总览

| 验收维度 | 需求条目 | 要求等级 | 达成版本 | 状态 |
|----------|----------|----------|----------|:--:|
| 知识问答机器人 | §六 | 必须完成 | v1.0 MVP | ✅ |
| 角色化 Agent | §七 | 必须完成 | v1.0 MVP | ✅ |
| 至少一个工具调用场景 | §九.1 | 必须完成 | v1.0 MVP | ✅ |
| 基础多轮对话能力 | §九.1 | 必须完成 | v1.0 MVP | ✅ |
| 基本文档交付 | §九.1 | 必须完成 | v1.0 MVP | ✅ |
| 成绩查询工具接入 | §九.2 | 推荐完成 | v1.0 MVP | ✅ |
| 学业分析建议 | §九.2 | 推荐完成 | v1.0 MVP | ✅ |
| 诗词鉴赏/人格化表达 | §九.2 | 推荐完成 | v2.3（昕哥） | ✅ |
| 情绪共情能力 | §九.2 | 推荐完成 | v1.0 MVP | ✅ |
| 问答来源展示 | §九.2 | 推荐完成 | v2.0 | ✅ |
| 更多角色设定 | §九.3 | 可选扩展 | v2.1 + v2.3 | ✅ |
| 任务历史记录 | §九.3 | 可选扩展 | v2.0 | ✅ |
| 用户反馈机制 | §九.3 | 可选扩展 | v2.1 | ✅ |
| Agent 偏好记忆 | §九.3 | 可选扩展 | v2.3 | ✅ |
| 风险动作人工确认 | §九.3 | 可选扩展 | v2.0 HITL | ✅ |
| 日志与监控 | §九.3 | 可选扩展 | v2.1 监控面板 | ✅ |
| 稳定性 | §十.1 | 非功能 | v1.0 MVP | ✅ |
| 可维护性 | §十.2 | 非功能 | v1.0 MVP | ✅ |
| 可扩展性 | §十.3 | 非功能 | v2.0 BaseTool | ✅ |
| 安全性 | §十.4 | 非功能 | v2.0 中间件 | ✅ |
| 用户体验 | §十.5 | 非功能 | v2.0~v2.3 | ✅ |

**总计 21 项验收条目，全部通过。**

---

## 二、验收依据与方法

本次验收不是只看演示效果，而是按“需求条目 → 代码实现 → 测试证据 → 构建验证”的链路做核对。主要依据包括：

1. 《二阶段项目需求文档》中的功能与非功能要求。
2. `agent_system/`、`frontend-vue/`、`model/` 中的实际实现代码。
3. `docs/testing/` 中沉淀的测试数据与回归文档。
4. 最终构建与回归结果，包括后端编译、前端构建、UI 静态检查和 Playwright 真浏览器回归。

验收方法分为四类：

1. **需求对照**：逐条比对需求项是否有对应实现。
2. **代码核对**：确认功能不是停留在文档里，而是已经落在接口、工具、模型或前端交互上。
3. **结果验证**：确认具备测试数据、运行结果或监控证据。
4. **边界审查**：避免把“一期最小闭环”写成“已经通用化完成”的过度表述。

---

## 三、从设计到验收的完整工作链路

### 3.1 架构决策阶段（v1.0 MVP 设计期）

在正式编码前完成了以下关键设计决策，记录于《Agent 系统架构说明文档（v1.0-MVP）》：

| 决策 | 选型 | 贯穿后续版本的效果 |
|------|------|-------------------|
| 局部嫁接，不重构主干 | `agent_system/` 独立于现有 `API/`、`service/`、`DAO/` | 四个版本迭代零次破坏原有学生/成绩/班级/就业模块 |
| Planner 驱动，受控执行 | 意图 → 计划 → 执行，不放开 LLM 自由选工具 | 每个环节可审计、可降级，出问题时可精准定位 |
| 现有能力先包装成工具 | 统一 `{success, error, data}` 返回格式 | v2.0 平滑重构为 BaseTool 子类，接口零断裂 |
| Persona 只在回复注入 | 意图分类保持客观 | v2.1 新增陪伴班主任、v2.3 新增昕哥，均未影响底层路由 |
| 不用 LangChain Agent 框架 | 自研 Planner → Executor 驱动 | 后续扩展到 8 个工具后，调用链仍保持可控、可追踪 |

**这一阶段最重要的判断**是：MVP 需要的不是“LLM 自主选工具”，而是“确定性、可审计的执行链路”。后续多个版本的扩展证明，这个判断是正确的。

### 3.2 底层框架重构与统一（v2.0）

v1.0 MVP 的工具层由四个独立模块组成：`score_tool`、`rag_tool`、`nl2sql_tool`、`student_tool`。v2.0 的关键工作，是把它们升级成一个可持续扩展的统一底座。

主要完成了三件事：

**（1）BaseTool + ToolContext 统一工具契约**

- `ToolContext` 统一封装 db session、user_id、username、user_role、session_id 等运行时依赖
- `BaseTool.run(ctx, step_params)` 统一工具入口
- 统一输出 `{success, error, ...}` 风格结果，Executor 不再关心工具内部实现差异

**（2）Executor 从硬编码分发改为注册表驱动**

v1.0 时代工具分发逻辑依赖 `if/elif`；v2.0 重构后统一走 `_TOOL_REGISTRY` 查表调用。这样后续新增 `weather_tool`、`email_tool`、`commute_plan_tool`、`nearby_service_tool` 时，Executor 核心逻辑无需继续膨胀。

**（3）PlanStep 扩展为链式执行**

新增 `params` 和 `inputs_from` 字段，支持工具间自动传值。例如：

- geocode 结果自动传入 weather 查询
- 通勤规划结果可作为邮件内容生成的上下文输入

这一步直接支撑了天气、通勤、周边服务以及 Supervisor 一期协作场景。

### 3.3 需求功能逐版本实现

下面按需求文档条目，逐项说明功能落在哪个版本、使用了哪些核心实现，以及对应的验收证据。

---

## 四、功能需求逐项验收

### 4.1 知识问答机器人（需求 §六）

| 子需求 | 实现版本 | 实现方式 |
|--------|----------|----------|
| 自然语言提问 | v1.0 MVP | `agent_api.py` → `agent_service.py` → `classify_intent()` → `knowledge_qa` |
| 基于知识库检索生成回答 | v1.0 MVP | `rag_tool.py` 调用 RAG 检索链路：知识库切片入库 → Milvus 混合检索 → CrossEncoder 精排 → LLM 总结 |
| 减少幻觉 | v1.0 MVP | QA 优先、来源注入、资料不足拒答、RAG 结果约束回答范围 |
| 语言自然清晰 | v1.0 MVP | Persona prompt 注入 + LLM 流式总结 |
| 展示依据来源 | v2.0 | 来源格式化为 `[来源 N \| 类型 \| 文件名]`，并由前端做对应展示 |

**关键文件**：`agent_system/tools/rag_tool.py`、`agent_system/executor/agent_executor.py`、`RAG/retrieval_service.py`

#### 4.1.1 RAG 功能架构与精度提升设计

本项目的知识问答不是“文档向量化后直接搜索”，而是按“检索前治理、检索中召回、检索后校准”的方式设计了一套完整 RAG 链路。这样做的目标很明确：让系统既能回答得准，也能在资料不足时明确拒答。

**（1）检索前：切片、字段和入库先保证知识质量**

RAG 入库阶段由 `RAG/ingestion.py` 负责，核心设计如下：

| 设计点 | 实现方式 | 验收价值 |
|--------|----------|----------|
| 多知识库隔离 | `RAG/config.py` 配置 `novels` 和 `production` 两套知识库 | 四大名著知识库与工程文档知识库互不污染，后续可继续扩库 |
| 多格式文档接入 | 工程文档支持 `.pdf`、`.docx`、`.md`，小说库支持 Markdown | 知识来源不局限于单一格式 |
| 结构化切片 | 四大名著按“第 X 回”切章节，Markdown 按标题切分，PDF 按页提取后识别标题，DOCX 优先读取标题样式 | 尽量保留文档原有结构，避免机械切片破坏语义 |
| 中文友好切片 | `chunk_size=500`、`chunk_overlap=50`，优先按段落、换行、句号、分号、逗号切分 | 保证片段既不过长，也不会把一句完整语义切断 |
| 标题注入正文 | 普通文档 chunk 生成 `【章节标题】正文` | 提升按主题、章节、场景提问时的召回率 |
| QA 字段治理 | QA 文件要求 `question`、`answer`、`reason` 字段完整 | 标准问答可直接用于高置信回答 |
| 统一入库字段 | 统一保存 `doc_id`、`text`、`question`、`answer`、`reason`、`file_name`、`chunk_index`、`total_chunks`、`source_type`、`dense_vector` | 后续检索、精排、引用、回退都能基于同一套结构工作 |
| 向量质量校验 | 入库前校验 embedding 数量和 1024 维向量维度 | 避免脏数据进入 Milvus 后影响检索质量 |

这部分的验收重点是：系统不是只关注“能不能入库”，而是提前把文档结构、QA 标准答案、来源字段、chunk 位置都治理好，为后面的精确召回打基础。

**（2）检索中：查询改写 + 混合检索 + 分阶段召回**

检索阶段由 `RAG/retrieval_service.py` 和 `RAG/retrieval.py` 负责，核心链路如下：

```text
用户问题
  ↓
rewrite_query 查询改写
  ↓
Embedding 向量化
  ↓
Milvus Hybrid Search
  ├─ Dense Vector：语义相似召回
  └─ BM25 Sparse Vector：关键词召回
  ↓
RRF 融合排序
  ↓
结构化 RetrievedChunk 输出
```

关键精度手段包括：

- 查询改写会把口语问题改成关键词密集查询，并保留人物名、项目名、容量、电压等级、单位、时间等限定信息。
- `prepare_query()` 会一次性完成改写和 embedding，QA 优先与原文回退时复用同一份查询结果，避免重复计算。
- Milvus 使用 Dense Vector + BM25 Sparse Vector 混合检索，既照顾语义相似，也照顾精确关键词命中。
- RRF 融合排序避免只依赖单一路召回结果，当前配置为 `hybrid_top_k=10`、`rrf_k=60`、`rrf_final_n=10`。
- 支持 `source_type == "qa"` 与 `source_type != "qa"` 的过滤检索，工程知识库可以先查标准 QA，再按需查原文。

这部分的验收重点是：系统不是单纯向量检索，而是同时利用语义召回、关键词召回和业务分层召回，降低“问得像但答错”和“关键词很准却搜不到”的风险。

**（3）检索后：精排、上下文扩展、去重、引用和拒答**

检索后的质量控制由 `RAG/rerank.py`、`RAG/prompt_builder.py`、`RAG/ask_service.py`、`RAG/generation.py` 共同完成。

| 环节 | 实现方式 | 精度价值 |
|------|----------|----------|
| CrossEncoder 精排 | 使用 `BAAI/bge-reranker-v2-m3` 对 `(query, candidate_text)` 成对打分，默认取 Top-3 | 比只看向量距离更适合判断“这个片段能不能回答这个问题” |
| 精排降级 | 精排失败时自动退回 RRF Top-K | 模型异常不影响基础问答可用性 |
| QA 直接回答 | `production` 知识库启用 QA 优先，达到 `qa_direct_threshold=0.82` 且领先幅度满足 `qa_margin_threshold=0.05` 时直接返回标准答案 | 高频标准问题不必再交给生成模型自由发挥 |
| 轻量校正 | QA 候选会规避“本项目”误命中“参考项目”等问题 | 降低工程文档中相似项目混淆 |
| 原文回退 | QA 不够稳时自动切换到 `source_type != "qa"` 的原文检索 | 兼顾标准答案和开放问题 |
| 保守拒答 | 工程库 `refuse_when_insufficient=True`，top score 低于 `retrieval_min_score=0.15` 时明确资料不足 | 防止检索证据不足时强行编答案 |
| small-to-big | 命中 chunk 后拉取前后相邻片段 | 避免只拿到半段上下文导致回答片面 |
| 去重与预算 | 先按 `(doc_id, chunk_index)` 去重，再按文本相似度软去重，并控制 `max_context_tokens=2000` | 提高上下文有效信息密度 |
| 来源引用 | 生成 `citations`，保留文件名、类型、chunk 序号、内容预览 | 前端可展示依据，验收时可追溯答案来源 |
| 生成兜底 | LLM 生成失败时返回检索来源预览 | 外部模型异常时仍能给用户可理解的结果 |

最终回答阶段的 prompt 明确要求“严格基于参考资料、引用来源、不编造”。因此，本项目的 RAG 精度提升不是只靠某一个模型，而是通过“入库质量 + 混合召回 + 精排校准 + 上下文治理 + 保守拒答”共同实现。

#### 4.1.2 RAG 与 Agent 子系统的集成方式

在 Agent 体系里，RAG 不是被业务代码直接散调用，而是统一包装成 `rag_tool` 接入 Executor：

1. 用户提出知识型问题。
2. Intent 识别为 `knowledge_qa`。
3. Planner 生成 RAG 工具调用步骤。
4. Executor 通过统一工具协议调用 `rag_tool`。
5. `rag_tool` 进入 RAG 检索链路，返回答案和来源。
6. 最终回复再叠加 Persona 表达风格。

这个设计保证了三个边界：

- RAG 负责“找依据、组织证据”，不直接决定 Agent 整体流程。
- Agent 负责“意图、计划、工具编排”，不侵入 RAG 内部检索细节。
- Persona 只影响最终表达，不影响检索结果和工具路由。

同时，RAG 控制器已做懒加载处理，问答和入库管线只有在真正使用时才加载，避免 `sentence_transformers`、DashScope、Milvus 客户端等重依赖挤占系统启动关键路径。这一点也体现了当前系统在“功能能力”和“启动性能”之间做了工程化隔离。

### 4.2 角色化 Agent（需求 §七）

#### 4.2.1 角色设计（§7.2）

| 角色 | 实现版本 | 关键特征 |
|------|----------|----------|
| 学业导师（academic_mentor） | v1.0 MVP | 温和、鼓励型，先肯定再建议 |
| 陪伴班主任（companion_head_teacher） | v2.1 | 共情型，不诊断、不承诺、危险话题引导联系专业人员 |
| 昕哥（xinge） | v2.3 | 称用户“好兄弟”，鼓励型，擅长复盘与纠错说明 |

`PERSONA_REGISTRY` 在 v1.0 就预留了扩展点，后续新增角色只需补充注册项和 system prompt，不影响底层意图分类与工具调用。

**关键文件**：`agent_system/prompts/persona_prompt.py`、`frontend-vue/src/views/AgentView.vue`

#### 4.2.2 角色设定与语言风格（§7.3）

每个角色都明确定义了：

- 身份定位
- 语言风格
- 能力范围
- 安全边界

其中陪伴班主任与昕哥均包含明确的风险边界声明，确保角色个性不会突破系统安全边界。

#### 4.2.3 学业辅导与诗词鉴赏（§7.4）

| 子需求 | 实现 | 关键文件 |
|--------|------|----------|
| 回答学习相关问题 | `knowledge_qa` + `academic_advice` 意图 | `planner/task_planner.py` |
| 成绩表现基础分析 | `student_tool` → `score_tool` → LLM 流式分析 | `tools/student_tool.py`、`tools/score_tool.py` |
| 适度学习建议 | LLM 总结时注入学业导师 Persona | `executor/agent_executor.py` |
| 诗词鉴赏/文学表达 | 昕哥 Persona + `emotional_support` / `knowledge_qa` 场景复用 | `prompts/persona_prompt.py` |

典型闭环如下：

1. 用户提出学业问题。
2. 系统识别 `academic_advice`。
3. Planner 生成 `student_tool` + `score_tool` 执行计划。
4. LLM 结合真实成绩数据与 Persona 风格，输出“先共情、再分析、再建议”的回答。

#### 4.2.4 情绪疏导与心理陪伴（§7.5）

| 子需求 | 实现 | 关键设计 |
|--------|------|----------|
| 共情逻辑（先理解再建议） | v1.0 MVP `emotional_support` 意图 + Persona prompt | 不走工具，直接走人格化回复 |
| 敏感捕捉 | v2.0 `input_guard.py` | 对提示注入、敏感操作、超长输入做拦截 |
| 边界约束 | v1.0 MVP 起每个 Persona 都明确定义 | 不诊断、不替代专业咨询、危险话题引导现实支持 |

**关键文件**：`agent_system/middleware/input_guard.py`、`agent_system/prompts/persona_prompt.py`

#### 4.2.5 调用工具能力（§7.6）

| 需求场景 | 工具 | 实现版本 | 说明 |
|----------|------|----------|------|
| 查询成绩 | `score_tool` | v1.0 MVP | 按学号查各科成绩 |
| 查询学生基本信息 | `student_tool` | v1.0 MVP | username → 学号映射，含权限策略 |
| 查询班级情况 | `nl2sql_tool` | v1.0 MVP | 覆盖开放式 SQL 查询 |
| 查询就业信息 | `nl2sql_tool` | v1.0 MVP | 复用 NL2SQL |
| 查询统计结果 | `nl2sql_tool` | v1.0 MVP | 复用 NL2SQL |
| RAG 知识型问答 | `rag_tool` | v1.0 MVP | QA 优先 + Milvus 混合检索 + CrossEncoder 精排 + 来源引用 |
| 天气查询 | `weather_tool` | v2.0 | geocode → weather，两步链；v2.1 接入 MCP |
| 邮件发送 | `email_tool` | v2.0 | LLM 生成 + 白名单校验 + HITL 确认 |
| 通勤规划 | `commute_plan_tool` | v2.2 | 地图能力 + 路线建议 |
| 周边生活服务 | `nearby_service_tool` | v2.3 | 周边 POI 检索 + 列表卡片 |

**工具接口统一历程**：

- v1.0 MVP：4 个工具，各自实现
- v2.0：统一重构为 BaseTool 子类
- v2.1~v2.3：新增工具继续按统一接口接入，Executor 核心零改动

#### 4.2.6 多轮对话能力（§7.7）

| 子需求 | 实现版本 | 实现方式 |
|--------|----------|----------|
| 记住当前对话主题 | v1.0 MVP | `conversation_memory.py` 复用 TalkSession / TalkMessage |
| 支持追问（指代消解） | v2.0 | `query_rewriter.py`：规则判断 + LLM 消歧 |
| 长对话不爆上下文 | v2.2 | `summary_memory.py`：会话摘要 + 最近 5 条原文 |
| 短会话不冗余摘要 | v2.2 | 短会话使用标题式摘要，避免过度压缩 |

**关键文件**：`agent_system/memory/conversation_memory.py`、`agent_system/memory/working_memory.py`、`agent_system/memory/summary_memory.py`

### 4.3 功能范围对照（需求 §九）

#### 必须完成（§9.1）

| # | 要求 | 状态 | 证据 |
|---|------|:--:|------|
| 1 | 可运行的知识问答机器人 | ✅ | `rag_tool.py` + `RAG/retrieval_service.py`，支持 QA 优先、混合检索、精排、拒答和来源引用 |
| 2 | 角色化 Agent | ✅ | 3 个 Persona + `PERSONA_REGISTRY` 扩展机制 |
| 3 | 至少一个可调用工具场景 | ✅ | 实际已交付 8 个工具：score / student / rag / nl2sql / weather / email / commute_plan / nearby_service |
| 4 | 基础多轮对话能力 | ✅ | 上下文记忆 + 指代消解 + 摘要压缩 |
| 5 | 基本文档交付 | ✅ | 见 §八交付文档清单 |

#### 推荐完成（§9.2）

推荐项已全部实现，包括：

- 成绩查询工具接入
- 学业分析建议
- 情绪共情能力
- 问答来源展示
- 诗词鉴赏/人格化表达

#### 可选扩展（§9.3）

可选扩展项也已全部实现，包括：

- 角色扩展：已从 1 个角色扩展为 3 个 Persona
- 任务历史：落地 AgentTask 表
- 用户反馈：落地 AgentFeedback + 点赞/点踩交互
- 偏好记忆：FloatingAgent 本地角色记忆
- 风险确认：HITL 规则系统
- 日志监控：Agent 监控面板

---

## 五、非功能需求验收

### 5.1 稳定性（§10.1）

> 不影响现有学生管理系统主业务流程。新增 AI 模块出错时，不应导致整个系统不可用。

实现策略：

- `agent_system/` 作为独立子系统存在，不侵入原有主业务目录
- 意图分类、计划生成、工具执行、地图能力等各层都具备降级策略
- MCP 不可用时天气/通勤/周边服务可自动回退 REST
- 输入异常在进入 Planner 前就被拦截，不拖垮后续链路

### 5.2 可维护性（§10.2）

> 新增 AI 模块需保持清晰结构，避免把 Agent 逻辑直接堆进原有业务文件。

实现策略：

- 采用分层目录结构：api / service / planner / executor / tools / middleware / memory / hitl / supervisor / schemas / prompts
- 工具逻辑统一收敛到 `tools/`
- Agent 数据独立建模，不复用原有业务表
- 角色、工具、卡片、HITL 规则都具备独立扩展点

### 5.3 可扩展性（§10.3）

> 后续应支持增加更多角色或更多工具，并支持继续扩展知识库范围。

实现策略：

- **加角色**：`PERSONA_REGISTRY` 增加配置即可，前端角色列表自动可见
- **加工具**：继承 BaseTool → 注册表加一行 → Planner 补计划
- **加 HITL 规则**：`escalation_rules.py` 按 `tool_name` 配置
- **加卡片类型**：后端补类型，前端补组件，未知类型安全忽略
- **扩知识库**：`RAG/config.py` 增加知识库配置，`RAG/ingestion.py` 支持 Markdown / PDF / DOCX 多格式结构化切片入库

### 5.4 安全性（§10.4）

| 要求 | 实现 | 版本 |
|------|------|:--:|
| 业务数据权限约束 | `student_tool` 权限映射 + `score_tool` 权限限制 | v1.0 |
| 情绪陪伴回答边界 | 每个 Persona 都有明确边界说明 | v1.0 |
| 高风险动作不自动执行 | HITL 确认机制：预览 → 用户确认 → 发送 | v2.0 |
| 输入安全检查 | `input_guard` + `policy_checker` + 中间件管线 | v2.0 |
| 邮件收件人白名单 | `email_whitelist.py` 防止任意地址发送 | v2.0 |
| HITL 通用化 | `escalation_rules.py` 按工具配置风险等级/文案/超时 | v2.1 |
| 周边服务避免绝对判断 | 展示数据来源和距离，不输出“最好”“最安全”等断言 | v2.3 |

### 5.5 用户体验（§10.5）

| 要求 | 实现 | 版本 |
|------|------|:--:|
| 回答自然可读 | Persona 驱动 LLM 流式回复 + Markdown 渲染 | v1.0 / v2.0 |
| 查询结果清楚 | 工具结果转自然语言总结 | v1.0 |
| 风格符合角色 | 每个 Persona 独立 system prompt | v1.0 |
| 流式打字机效果 | SSE 分阶段事件（intent → plan → tool → chunk → done） | v1.0 |
| 全局入口 | FloatingAgent 悬浮按钮 + 侧面板 | v2.0 |
| 角色选择器 | CustomSelect 组件，支持 emoji 标识与键盘导航 | v2.0 / v2.3 |
| 结构化卡片 | WeatherCard / RouteCard / PoiListCard | v2.1~v2.3 |
| 反馈交互 | 点赞/点踩 + 原因输入 + 提交锁定 | v2.1 |
| 历史摘要 | 右侧摘要栏，短会话标题式摘要 | v2.2 |
| 主题跟随 | 卡片读取项目 CSS 变量，不污染全局主题 | v2.2~v2.3 |
| 系统管理导航效率 | 折叠态 emoji rail + 展开定位当前模块 + 子功能上下文记忆 | v2.3 |
| Agent 监控首屏可用性 | 进入 `sys-agent-monitor` 后默认自动加载近 7 天数据，无需手动刷新 | v2.3 |

---

### 5.6 运维观测与后台性能补强

在功能验收之外，v2.3 末段还补齐了几项非常有价值的运维侧增强：

1. **监控接口聚合**
   - 前端由多组监控接口并发请求，收敛为 `/agent/admin/dashboard` + `/agent/admin/tasks`
   - 后端统一输出总览、趋势、意图、工具、provider、差评原因和 MCP 健康状态

2. **监控查询索引补齐**
   - 为 `agent_task.create_time`
   - `agent_task.status`
   - `agent_task.intent`
   三个高频筛选字段补齐索引
   - 并在 `init_db()` 阶段对老库自动补建索引，避免只改模型但历史库不生效

3. **监控首屏自动加载**
   - 用户进入 Agent 监控子功能后，默认自动展示近 7 天数据
   - 不再要求管理员手动点击“刷新”

这说明当前监控面板已经不只是“能看”，而是开始兼顾**性能、首屏可用性和后台运维体验**。

---

## 六、架构演进全景

从 v1.0 到 v2.3，Agent 系统经历了四轮迭代，目录结构从 MVP 的基础模块扩展为完整子系统：

```text
agent_system/
├── api/agent_api.py              # 路由层：chat / stream / confirm / feedback / admin
├── service/agent_service.py      # 编排层：中间件 → 意图 → 计划 → 执行 → 记忆 → 持久化
├── planner/                      # 意图分类（11类）+ 计划生成（LLM + 兜底）
├── executor/agent_executor.py    # 通用执行引擎：注册表分发 + inputs_from + HITL + cards
├── tools/                        # 8 个工具，统一 BaseTool 子类
│   ├── base.py
│   ├── score_tool.py / student_tool.py / rag_tool.py / nl2sql_tool.py
│   ├── weather_tool.py
│   ├── email_tool.py
│   ├── commute_plan_tool.py
│   ├── nearby_service_tool.py
│   ├── mcp_client.py
│   └── email_whitelist.py
├── middleware/                   # 输入中间件与业务校验
├── memory/                       # 会话记忆、摘要记忆、上下文组装
├── hitl/                         # 人工确认机制
├── supervisor/                   # 多 Agent 一期编排
├── schemas/                      # 数据模型
└── prompts/                      # Intent / Persona / Planner Prompt
```

每个版本的增量变化如下：

| 版本 | 主题 | 新建文件 | 修改文件 | 核心交付 |
|------|------|:--:|:--:|------|
| v1.0 MVP | 学业导师单角色 + 4 工具 | 25 | 7 | RAG 问答、意图分类、Planner 驱动执行、SSE 流式、多轮记忆 |
| v2.0 | 多角色多工具 + 中间件 + HITL + 数据表 | 16 | 12 | BaseTool 统一接口、天气/邮件工具、输入中间件、HITL、AgentTask/Feedback 表、全局悬浮 Agent |
| v2.1 | 运营闭环与可观测 | ~8 | ~8 | 反馈闭环、监控面板、HITL 规则系统、MCP 底座、陪伴班主任、天气卡片 |
| v2.2 | 记忆压缩 + 地图通勤 + 卡片 + 回归护栏 | ~10 | ~6 | working/summary_memory、commute_plan_tool、route 卡片、UI 回归脚本、历史摘要布局 |
| v2.3 | 周边服务 + 监控增强 + Supervisor 一期 + 体验收口 | ~7 | ~10 | nearby_service_tool、poi_list 卡片、监控增强、Supervisor 最小闭环、昕哥角色、WeatherCard 复用 |

---

## 七、能力矩阵总表

| 能力域 | 当前状态 | 支撑版本 |
|--------|----------|----------|
| 意图识别 | 11 类意图（含 general_chat 与 supervisor_multi_agent） | v1.0→v2.3 |
| 工具调用 | 8 个工具，统一 BaseTool 接口 | v2.0 |
| 流式回复 | SSE 分阶段事件流 | v1.0→v2.0 |
| 多轮上下文 | 会话摘要 + 最近 5 条原文 | v2.2 |
| 输入安全 | 3 层中间件 + LangGraph 业务校验 | v2.0→v2.3 |
| HITL 确认 | 规则化风险确认，支持超时/取消/回写 | v2.0→v2.1 |
| MCP 能力底座 | 地图能力底座已服务天气/通勤/周边 3 条业务链 | v2.1→v2.3 |
| RAG 检索工程 | 多知识库、多格式入库、混合检索、CrossEncoder 精排、small-to-big、来源引用与保守拒答 | v1.0→v2.3 |
| 结构化卡片 | weather / route / poi_list 三类卡片，支持版本控制 | v2.1→v2.3 |
| 用户反馈 | 任务级点赞/点踩 + 原因输入 + 历史锁定 | v2.1→v2.2 |
| 运营监控 | 状态/意图/工具/provider/差评/任务详情可见 | v2.1→v2.3 |
| Persona | 3 个角色，统一注册表管理 | v1.0→v2.3 |
| 多 Agent 协作 | Supervisor 最小闭环：路线规划 + 邮件通知 | v2.3 |
| UI 回归 | 172 项静态检查 + 4 个 Playwright 真浏览器回归场景 | v2.2→v2.3 |
| 全局入口 | FloatingAgent 悬浮按钮 + `/agent` 全页入口 | v2.0 |

---

## 八、交付文档清单

对照需求文档 §十二的文档要求，当前已交付如下内容。

### 8.1 需求与设计文档

- `docs/Agent系统架构说明文档（v1.0-MVP）.md`
- `docs/Agent系统v2.0迭代总结与下版本规划.md`
- `docs/Agent系统v2.1功能需求设计.md`
- `docs/Agent系统v2.1迭代总结与下版本规划.md`
- `docs/Agent系统v2.2迭代总结与下版本规划.md`
- `docs/Agent系统v2.3迭代总结与下版本规划.md`
- `docs/Agent系统介绍演讲稿.html.md`

### 8.2 表设计与模型文档

- `model/AgentTask.py`
- `model/AgentFeedback.py`
- `model/TalkSession.py`
- `model/TalkMessage.py`

### 8.3 接口设计与接口清单

| 端点 | 方法 | 用途 | 版本 |
|------|------|------|:--:|
| `/agent/chat` | POST | 同步聊天 | v1.0 |
| `/agent/chat/stream` | POST | SSE 流式聊天 | v1.0 |
| `/agent/sessions` | GET | 会话列表 | v1.0 |
| `/agent/sessions/{id}/messages` | GET | 历史消息 | v1.0 |
| `/agent/personas` | GET | 角色列表 | v1.0 |
| `/agent/step/confirm` | POST | HITL 确认/取消 | v2.0 |
| `/agent/feedback` | POST | 提交反馈 | v2.1 |
| `/agent/admin/dashboard` | GET | 监控聚合大盘 | v2.3 |
| `/agent/admin/metrics` | GET | 监控聚合指标 | v2.1 |
| `/agent/admin/metrics/timeseries` | GET | 每日调用趋势 | v2.1 |
| `/agent/admin/metrics/intents` | GET | 意图排行 | v2.1 |
| `/agent/admin/metrics/tools` | GET | 工具统计 | v2.1 |
| `/agent/admin/metrics/providers` | GET | provider 分布 | v2.3 |
| `/agent/admin/metrics/feedback-reasons` | GET | 差评原因聚合 | v2.3 |
| `/agent/admin/tasks` | GET | 最近任务列表 | v2.1 |
| `/agent/admin/mcp/tencent-map/health` | GET | MCP 健康检查 | v2.1 |

### 8.4 开发计划与迭代文档

每版迭代文档均包含：

- 版本定位与主题
- 迭代范围与优先级
- 实施顺序建议
- 下版本规划

其中 v2.0 文档额外记录了 grill-me 设计讨论收敛出的关键决策。

### 8.5 测试文档（超额交付）

当前 `docs/testing/` 已累计 36 份测试数据与回归说明文档，覆盖：

- 反馈闭环
- 监控面板
- HITL 规则系统
- 腾讯地图 MCP 底座
- Persona 测试
- 天气、路线、周边卡片
- 记忆系统
- UI 回归与布局回归
- Supervisor 一期协作
- 监控首屏自动加载
- 侧栏折叠记忆与后台导航体验

### 8.6 协议与规范文档（超额交付）

- `docs/Agent卡片协议v1.md`
- `docs/Agent接入改造设计文档（AI执行规范）.md`

---

## 九、工程质量验证

每个版本都执行并通过以下验证：

```text
python -m compileall agent_system DAO model main.py
npm.cmd run build
npm.cmd run test:ui-regression
```

当前文档对应的最新验证结果：

```text
后端编译：通过
前端生产构建：通过
UI 回归检查：172/172 通过
Playwright UI 回归：4/4 通过
```

这些结果说明：

- 功能不仅“能写出来”，而且“能编过、能构建、能回归”
- Agent 子系统已经具备持续迭代时的质量护栏

---

## 十、验收边界说明

为了保证验收文档真实可信，这里明确说明当前范围边界：

1. **Supervisor 多 Agent 当前是一期最小闭环。**
   已完成“路线规划 + 邮件通知”跨域协作，但不夸大为通用自治多 Agent 平台。

2. **Persona 偏好记忆当前是轻量体验能力。**
   角色偏好保存在 localStorage，用于体验连续性，不做长期画像。

3. **地图能力当前以 MCP 为优先、REST 为兜底。**
   这代表系统具备较强可用性，但也说明地图能力受外部服务状态影响时仍需关注运营监控。

这三点不会影响本次验收通过结论，但有助于后续版本规划更加清晰。

---

## 十一、总结

### 从设计到验收，这个子系统真正完成了什么

1. **完成了功能交付。**
   从 RAG 知识问答、成绩分析、天气、邮件、通勤、周边服务，到多轮对话、Persona、Supervisor 一期协作，需求文档中的核心能力均已落地。

2. **完成了架构收敛。**
   通过 Planner → Executor、BaseTool、ToolContext、卡片协议、HITL 规则等机制，把功能堆叠变成了体系化扩展。

3. **完成了安全与治理闭环。**
   输入安全、中间件、白名单、人工确认、反馈闭环、监控面板共同构成了可治理的生产化路径。

4. **完成了工程化落地。**
   后端编译、前端构建、测试文档、UI 回归、协议文档、迭代总结全部齐备，说明这不是一次性 Demo，而是可持续演进的子系统。

### 一句话结论

**Agent 系统从 v1.0 MVP 到 v2.3，已经全面达到并部分超额完成《二阶段项目需求文档》中的验收要求；更重要的是，它不是“功能点拼装完成”，而是已经形成了一套可控、可维护、可扩展、可观测、可回归的工程化 Agent 子系统。**
