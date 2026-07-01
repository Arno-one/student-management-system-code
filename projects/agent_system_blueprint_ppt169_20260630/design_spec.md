# Agent 系统工程化蓝图汇报 - Design Spec

> Human-readable design narrative. Execution contract is `spec_lock.md`.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | Agent 系统工程化蓝图汇报 |
| **Canvas Format** | PPT 16:9 (1280x720) |
| **Page Count** | 16 |
| **Design Style** | `pyramid` narrative + `blueprint` visual style |
| **Target Audience** | 项目验收老师、技术答辩评委、课程指导教师，以及需要快速理解 Agent 子系统工程价值的项目组成员 |
| **Use Case** | Agent 子系统项目验收、技术蓝图汇报、现场演示前置说明 |
| **Delivery Purpose** | `presentation` 演讲型；正文基线 32px，页面以一页一个结论为主 |
| **Content Strategy** | 事实、版本、指标和验收结论严格来自两份源文档；允许重组为“结论先行 -> 技术蓝图 -> 能力矩阵 -> 验收证据 -> 演示路径”的汇报叙事 |
| **Created Date** | 2026-06-30 |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280x720 |
| **viewBox** | `0 0 1280 720` |
| **Margins** | left/right 56px, top 44px, bottom 40px |
| **Content Area** | 1168x636 |

---

## III. Visual Theme

### Theme Style

- **Mode**: `pyramid`。先给结论，再用架构、矩阵、表格、公式逐层证明。
- **Visual style**: `blueprint`。深色工程图纸、网格底、结构线、节点拓扑、标注线。
- **Theme**: Dark theme.
- **Tone**: 学术、工程、克制、可验证；用少量高亮制造“验收通过”的确定感。

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#05070D` | 暗场主背景 |
| **Secondary bg** | `#111827` | 面板、表格底、代码块底 |
| **Primary** | `#7DD3FC` | 蓝图线框、模块边框、主路径 |
| **Accent** | `#F59E0B` | 通过结论、关键数字、最终答案 |
| **Secondary accent** | `#8B5CF6` | RAG、MCP、Supervisor 等辅助能力路径 |
| **Body text** | `#F8FAFC` | 主文字 |
| **Secondary text** | `#B6C2D2` | 说明、脚注、表格次级文字 |
| **Tertiary text** | `#7F8EA3` | 页码、来源、微标注 |
| **Border/divider** | `#2A3A52` | 表格线、卡片线、维度线 |
| **Success** | `#22C55E` | 已通过、稳定状态 |
| **Warning** | `#F97316` | 风险动作、HITL、边界提醒 |
| **Grid** | `#1C2A3D` | 低透明网格与工程辅助线 |
| **Overlay** | `#05070D` | 图片上方可读性遮罩 |

### AI Image Strategy

- **Image Rendering**: `blueprint`
- **Image Palette**: `tech-neon`
- **Usage**: 只生成少量蓝图类主视觉。封面、章节转场、结尾使用 AI 蓝图/系统拓扑背景；架构图、能力矩阵、验收表格、公式全部用原生 SVG 绘制。

---

## IV. Typography System

### Font Plan

**Typography direction**: 工程蓝图无衬线 + 代码/组件名局部等宽。

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | `Microsoft YaHei` | `Arial` | `sans-serif` |
| **Body** | `Microsoft YaHei` | `Arial` | `sans-serif` |
| **Emphasis** | `Microsoft YaHei` | `Arial` | `sans-serif` |
| **Code** | `Microsoft YaHei` | `Consolas`, `Courier New` | `monospace` |

**Per-role font stacks**

- Title: `"Microsoft YaHei", Arial, sans-serif`
- Body: `"Microsoft YaHei", Arial, sans-serif`
- Emphasis: `"Microsoft YaHei", Arial, sans-serif`
- Code: `Consolas, "Microsoft YaHei", "Courier New", monospace`

### Font Size Hierarchy

| Role | Size |
| ---- | ---- |
| Cover title | 82 |
| Section title | 60 |
| Page title | 52 |
| Subtitle | 36 |
| Lead / core message | 34 |
| Body | 32 |
| Subheading | 30 |
| Annotation | 22 |
| Footnote | 16 |
| Hero number | 76 |

---

## V. Layout Principles

### Page Structure

- **Header area**: 44-110px；标题、页码、章节编码、坐标标注。
- **Content area**: 520-590px；结构图、矩阵、表格和公式为主。
- **Footer area**: 36-44px；来源、版本范围、演示节奏提示。

### Layout Pattern Library

| Pattern | Usage in this deck |
| ------- | ------------------ |
| Single-focus blueprint poster | P01, P03, P16 |
| KPI cards / metric strip | P02, P09 |
| Layered architecture | P04 |
| Process flow / controlled execution chain | P05 |
| Pipeline with stages | P06 |
| Vertical pillars | P07, P10 |
| Timeline | P08 |
| Hub-spoke / capability map | P11 |
| Client-server / multi-agent flow | P12 |
| Basic / consulting table | P09, P13 |
| Roadmap / demo path | P14 |
| Formula + interpretation split | P03, P05, P15 |

### Spacing Specification

| Element | Current Project |
| ------- | --------------- |
| Safe margin | 56px horizontal, 44px top |
| Content block gap | 28-40px |
| Icon-text gap | 12px |
| Card gap | 22px |
| Card padding | 22px |
| Card border radius | 6px; blueprint风尽量小圆角 |
| Line weight | 1.2-2px for schema lines; 3px only for highlighted path |

---

## VI. Icon Usage Specification

### Source

- **Built-in icon library**: `chunk-filled`
- **Usage method**: `<use data-icon="chunk-filled/<name>" .../>`
- **Rationale**: 该库直线几何、实心、锐利，适合工程蓝图和结构图。

### Recommended Icon List

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| 验收通过 | `chunk-filled/circle-checkmark` | P02, P09 |
| 架构模块 | `chunk-filled/layers` | P04 |
| 受控执行 | `chunk-filled/route` | P05 |
| RAG 检索 | `chunk-filled/magnifying-glass` | P06 |
| 工具注册表 | `chunk-filled/code-block` | P07 |
| 版本演进 | `chunk-filled/arrows-rotate-clockwise` | P08 |
| 监控观测 | `chunk-filled/chart-line` | P11 |
| 安全边界 | `chunk-filled/shield-check` | P10 |
| 数据库/知识库 | `chunk-filled/database` | P06 |
| 邮件/通信 | `chunk-filled/mailbox` | P12 |
| 地图能力 | `chunk-filled/map` | P12 |
| 用户/Persona | `chunk-filled/users` | P02, P10 |
| AI 子系统 | `chunk-filled/robot` | P01 |
| 文档交付 | `chunk-filled/files` | P13 |
| 演示播放 | `chunk-filled/circle-play` | P14 |

---

## VII. Visualization Reference List

Catalog read: 71 templates

| Page | Template | Path | Summary-quote (verbatim from `charts_index.json`) | Usage |
| ---- | -------- | ---- | ------------------------------------------------- | ----- |
| P02 | kpi_cards | `templates/charts/kpi_cards.svg` | "Pick for 4-8 standalone numeric metrics shown as overview cards (2x2 or 1x4) — exec summary opener, dashboard headline, quarterly recap, results-at-a-glance. Skip if metrics have target baselines (use bullet_chart) or single hero number (use gauge_chart)." | 展示 11 类意图、8 个工具、3 个 Persona、3 类卡片、21 项验收通过等核心数字 |
| P04 | layered_architecture | `templates/charts/layered_architecture.svg` | "Pick for 3-4 horizontal architecture layers (presentation/service/data), 2-4 module cards per layer, each card = title + 1-line description (description required, even if source brief). Skip if no per-module descriptions (use icon_grid) or no horizontal layering (use module_composition)." | 展示 Agent 子系统独立目录、API/service/planner/executor/tools/memory/hitl 等分层 |
| P05 | process_flow | `templates/charts/process_flow.svg` | "Pick for 3-8 sequential steps connected by simple arrows — approval workflows, customer onboarding, request handling, lifecycle stages. Skip if cyclical (use circular_stages) or stages produce named outputs (use pipeline_with_stages)." | 展示 意图分类 -> 计划生成 -> Executor -> 工具链 -> Persona 回复 |
| P06 | pipeline_with_stages | `templates/charts/pipeline_with_stages.svg` | "Pick for 3-5 horizontal pipeline stages, each = title + 1-line description + output artifact, connected by arrows (data pipelines, ETL, build pipelines). Skip if any stage lacks an artifact (use process_flow or numbered_steps)." | 展示 RAG 入库治理、混合召回、精排、small-to-big、来源引用与拒答 |
| P07 | vertical_pillars | `templates/charts/vertical_pillars.svg` | "Pick for 1×3 / 1×4 / 1×5 vertical column layout where each pillar = one independent category with title + bullets — PEST (Political/Economic/Social/Technological), four-pillar strategy overview, side-by-side independent categories. Skip for 2×2 quadrant (use quadrant_text_bullets), pricing tiers (use comparison_columns), or 2×2 parallel aspects (use labeled_card)." | 展示 BaseTool、ToolContext、注册表、PlanStep 链式执行 |
| P08 | timeline | `templates/charts/timeline.svg` | "Pick for 3-8 milestone events on a horizontal time axis (no duration). Skip for tasks with start/end ranges (use gantt_chart) or vertical layout (use roadmap_vertical)." | 展示 v1.0 -> v2.3 版本演进 |
| P09 | consulting_table | `templates/charts/consulting_table.svg` | "Pick for high-density tables with embedded micro bar visuals (consulting/financial reports). Skip for plain text data (use basic_table)." | 展示 21 项验收条目及通过状态 |
| P10 | vertical_pillars | `templates/charts/vertical_pillars.svg` | "Pick for 1×3 / 1×4 / 1×5 vertical column layout where each pillar = one independent category with title + bullets — PEST (Political/Economic/Social/Technological), four-pillar strategy overview, side-by-side independent categories. Skip for 2×2 quadrant (use quadrant_text_bullets), pricing tiers (use comparison_columns), or 2×2 parallel aspects (use labeled_card)." | 展示 稳定性、可维护性、可扩展性、安全性、用户体验 |
| P11 | hub_spoke | `templates/charts/hub_spoke.svg` | "Pick for 1 core capability + 4-8 surrounding capabilities (platform/ecosystem); each spoke = title or title + 1-2 line description. Skip if center is a system containing parts with their own descriptions (use module_composition), or surroundings exert inward pressure on the center (use hub_inward_arrows)." | 展示 AgentTask、AgentFeedback、监控面板、provider、差评原因、MCP 健康状态 |
| P12 | client_server_flow | `templates/charts/client_server_flow.svg` | "Pick for left-side clients + right-side servers with labeled bidirectional arrows for key interactions (request/response/push). Each module = name + 1-line description; each arrow must have an action label. Skip for non-distributed flows (use process_flow)." | 展示 Supervisor、MapAgent、CommunicationAgent 与地图/邮件工具协作 |
| P13 | basic_table | `templates/charts/basic_table.svg` | "Pick for plain tabular text/number grid, 3-8 columns. Skip if cells need visual bars (use consulting_table) or qualitative scores (use harvey_balls_table)." | 展示交付文档、接口、模型、测试文档和协议文档 |
| P14 | roadmap_vertical | `templates/charts/roadmap_vertical.svg` | "Pick for 4-8 milestones on a vertical timeline with status indicators. Skip for horizontal time emphasis (use timeline) or tasks with durations (use gantt_chart)." | 展示现场演示路径 |

**Runners-up considered**

- `icon_grid` | rejected for P02: 核心是数字概览，不只是平行能力图标。
- `module_composition` | rejected for P04: 源内容有明确横向层级，layered_architecture 更贴合。
- `numbered_steps` | rejected for P05: 需要箭头表达受控执行链，process_flow 更直接。
- `basic_table` | rejected for P09: 验收总览需要更强的咨询汇报密度与状态编码。

---

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Acquire Via | Status | Reference | text_policy | page_role |
| -------- | ---------- | ----- | ------- | ---- | -------------- | ----------- | ------ | --------- | ----------- | --------- |
| cover_blueprint_bg.png | 1672x941 | 1.78 | 封面系统蓝图背景，SVG 标题叠加 | Background | #1 full-bleed background with floating title + #29 two-stop scrim | ai | Generated | 学生管理系统 Agent 子系统的抽象工程蓝图，中央为 AI 节点，周围是工具、RAG、HITL、监控节点拓扑 | none | hero_page |
| transition_topology_bg.png | 1672x941 | 1.78 | P03/P15 的章节级蓝图背景 | Background | #44 background image + native network/architecture diagram | ai | Generated | 可控、可扩展、可观测、可回归四个能力围绕 Agent 核心形成拓扑网络 | none | hero_page |
| closing_blueprint_bg.png | 1672x941 | 1.78 | 结尾页蓝图收束背景 | Background | #1 full-bleed background with floating title + #29 two-stop scrim | ai | Generated | 一套长期运行的 Agent 工程体系从聊天框演进为可运营子系统，线框逐步闭合成稳定回路 | none | hero_page |
| formula_engineering_value.png | 981x50 | 19.62 | P03 工程价值公式 | Latex Formula | formula-block | formula | Rendered | `E_{Agent}=C_{control}+X_{extend}+O_{observe}+R_{regress}` | | |
| formula_tool_risk.png | 809x50 | 16.18 | P05 工具调用风险公式 | Latex Formula | formula-block | formula | Rendered | `Risk_{LLM}=P_{skip}+P_{wrong tool}+P_{repeat}` | | |
| formula_acceptance_rate.png | 511x101 | 5.06 | P09 验收通过率公式 | Latex Formula | formula-block | formula | Rendered | `PassRate=21/21=100%` | | |

---

## IX. Content Outline

### Part 1: 结论先行

#### Slide 01 - 这不是聊天框，是可运营的 Agent 工程体系

- **Cover impact**: 用“从聊天框到工程体系”的冲突作为钩子；全屏蓝图拓扑背景，标题浮在左下，右侧呈现 Agent 核心节点。
- **Layout**: Full-bleed blueprint background + floating title + 3 个验收标签。
- **Title**: 学生管理系统 Agent 子系统工程化蓝图
- **Subtitle**: 从 v1.0 MVP 到 v2.3 的可控、可扩展、可观测、可回归体系
- **Core message**: 这个项目交付的不是一个会聊天的入口，而是一套能嵌入现有业务系统长期运行的 Agent 子系统。
- **Content**: 版本范围 v1.0 MVP -> v2.3；交付 11 类意图、8 个工具、3 个 Persona、3 类卡片、1 套 HITL、1 套 RAG 链路、1 个地图 MCP 底座、1 个 Supervisor 最小闭环。

#### Slide 02 - 核心交付已经从功能点升级为工程能力矩阵

- **Layout**: KPI cards + bottom proof strip.
- **Core message**: 当前系统已形成“能力、协议、治理、回归”四类资产，不再只是单点功能。
- **Visualization**: `kpi_cards`
- **Content**: 11 类意图识别；8 个业务工具；3 个 Persona；3 类结构化卡片；21 项验收条目全部通过；36 份测试文档沉淀；172/172 UI 静态检查通过；Playwright 4/4 回归通过。

#### Slide 03 - 工程价值来自四个可验证维度，而不是功能数量

- **Layout**: Formula hero + four-axis interpretation.
- **Core message**: Agent 的工程价值可以被拆成可控、可扩展、可观测、可回归四个维度。
- **Visualization**: native formula + four-node blueprint ring.
- **Content**: `E_Agent = C_control + X_extend + O_observe + R_regress`。可控对应 Planner/Executor/HITL；可扩展对应 BaseTool/ToolContext/卡片协议；可观测对应 AgentTask/Feedback/监控面板；可回归对应 UI 静态检查和 Playwright。

### Part 2: 技术蓝图

#### Slide 04 - 局部嫁接让 Agent 演进不污染原业务主干

- **Layout**: Layered architecture.
- **Core message**: `agent_system/` 作为独立子系统与原有 API/service/DAO 平行，降低了改造风险。
- **Visualization**: `layered_architecture`
- **Content**: 表现层包含 FloatingAgent 与 `/agent` 全页入口；编排层包含 `agent_service.py`、中间件、意图分类、Planner、Executor；能力层包含 8 个工具、RAG、地图 MCP、邮件；治理层包含 memory、HITL、feedback、admin metrics；原业务层保持学生、成绩、班级、就业模块边界。

#### Slide 05 - Planner 驱动把工具调用风险收敛到确定性链路

- **Layout**: Process flow with risk formula.
- **Core message**: 系统不让 LLM 自由拍板工具，而是让计划和注册表控制执行。
- **Visualization**: `process_flow`
- **Content**: 意图分类 -> 计划生成 -> Executor 按结构化步骤执行 -> BaseTool 统一返回 -> Persona 只影响最终表达。风险公式 `Risk_LLM = P_skip + P_wrong tool + P_repeat` 对应“不调、调错、重复调”的三类风险，受控链路正是为降低它们。

#### Slide 06 - RAG 不是向量库接入，而是一条问答质量工程链

- **Layout**: Pipeline with stages.
- **Core message**: RAG 的亮点在于检索前治理、检索中混合召回、检索后校准以及资料不足拒答。
- **Visualization**: `pipeline_with_stages`
- **Content**: 入库治理保留章节边界、标题注入、500 字 chunk 与 50 字 overlap；检索阶段使用查询改写、Dense Vector、BM25、RRF；精排阶段使用 CrossEncoder；生成前做 small-to-big、去重、token 预算和来源引用；资料不足时明确拒答。

#### Slide 07 - v2.0 的真正转折是统一底座，而不是堆新工具

- **Layout**: Four vertical pillars.
- **Core message**: BaseTool、ToolContext、注册表和 PlanStep 链式执行把工具扩展成本压低。
- **Visualization**: `vertical_pillars`
- **Content**: BaseTool 统一入口；ToolContext 封装 db、user、session；`_TOOL_REGISTRY` 替代 if/elif；PlanStep 支持 `params` 与 `inputs_from`，让 geocode、weather、email 等工具可以自动传值协作。

#### Slide 08 - 四轮版本演进逐步从“可运行”走向“可运营”

- **Layout**: Horizontal timeline.
- **Core message**: v1.0 验证闭环，v2.0 统一底座，v2.1 建立运营观测，v2.2 补长期可用能力，v2.3 收口体验和协作。
- **Visualization**: `timeline`
- **Content**: v1.0 交付知识问答、多轮对话、学业导师和 SSE；v2.0 交付多角色、多工具、中间件、HITL、AgentTask/Feedback；v2.1 交付反馈闭环、监控面板、MCP 底座和天气卡片；v2.2 交付记忆压缩、通勤规划、UI 回归；v2.3 交付周边服务、POI 卡片、Supervisor 最小闭环、监控增强和性能收口。

### Part 3: 验收证据

#### Slide 09 - 21 项验收条目全部通过，结论可以先给

- **Layout**: Acceptance table + formula.
- **Core message**: 功能需求、扩展需求和非功能需求均已达成，验收通过率为 100%。
- **Visualization**: `consulting_table`
- **Content**: 必须完成 5 项全部通过；推荐完成 5 项全部通过；可选扩展 6 项全部通过；非功能 5 项全部通过。公式 `PassRate = 21 / 21 = 100%` 作为页面主结论。

#### Slide 10 - 非功能验收证明它不是一次性 Demo

- **Layout**: Five vertical pillars.
- **Core message**: 稳定性、可维护性、可扩展性、安全性和用户体验都有对应工程抓手。
- **Visualization**: `vertical_pillars`
- **Content**: 稳定性来自独立子系统和降级策略；可维护性来自分层目录和独立数据模型；可扩展性来自工具、角色、卡片、HITL、知识库扩展点；安全性来自权限、输入中间件、邮件白名单和人工确认；用户体验来自流式回复、全局入口、角色选择、结构化卡片和反馈交互。

#### Slide 11 - 可运营性来自任务、反馈、监控和健康状态的闭环

- **Layout**: Hub-spoke capability map.
- **Core message**: 系统好不好用不靠主观判断，而是由任务、反馈、provider、差评原因和 MCP 健康状态支撑。
- **Visualization**: `hub_spoke`
- **Content**: 中心为 Agent 运营面板；外围包括 AgentTask、AgentFeedback、意图分布、工具统计、provider 分布、差评原因聚合、最近任务详情、MCP 健康状态。v2.3 将监控接口收敛为 `/agent/admin/dashboard` 和 `/agent/admin/tasks`。

#### Slide 12 - Supervisor 最小闭环证明多 Agent 协作已经跨域跑通

- **Layout**: Client-server flow.
- **Core message**: 多 Agent 没有追求大而全，而是通过“路线规划 + 邮件通知”完成一条可验证跨域链路。
- **Visualization**: `client_server_flow`
- **Content**: 示例场景为“从宝安中心到龙岗怎么走，并顺手写一封邮件通知老师”。Supervisor 负责任务拆解与状态汇总；MapAgent 复用通勤规划工具；CommunicationAgent 复用邮件工具；HITL 保证高风险动作确认。

#### Slide 13 - 文档、接口、模型和测试沉淀让交付可复查

- **Layout**: Dense table with document clusters.
- **Core message**: 交付物覆盖需求设计、模型、接口、迭代计划、测试和协议规范，验收证据链完整。
- **Visualization**: `basic_table`
- **Content**: 需求与迭代文档覆盖 v1.0 到 v2.3；模型包括 AgentTask、AgentFeedback、TalkSession、TalkMessage；接口包括 chat、stream、sessions、personas、confirm、feedback、admin dashboard、tasks、MCP health；测试文档覆盖反馈、监控、HITL、MCP、Persona、天气、路线、周边、记忆、UI 回归、Supervisor 和后台导航体验。

### Part 4: 演示路径与收束

#### Slide 14 - 现场演示应先给用户体验，再揭示后台治理

- **Layout**: Vertical roadmap.
- **Core message**: 最顺的演示路径是先看用户侧，再看运营侧，最后回到架构价值。
- **Visualization**: `roadmap_vertical`
- **Content**: 第一步说明目标：不是聊天框，是 Agent 工程体系；第二步展示主对话页、Persona、结构化卡片、快捷工具；第三步展示反馈闭环和监控面板；第四步讲 Planner、BaseTool、HITL、Supervisor 的架构价值。

#### Slide 15 - 最小闭环已经闭上，下一步重点是治理复杂度

- **Layout**: Formula + roadmap split.
- **Core message**: 后续优化不应只横向加功能，而应继续提升能力治理、冷启动、观测和回归效率。
- **Visualization**: native formula + roadmap markers.
- **Content**: 当前系统已经把“能力、协议、体验、观测”收口。下一步建议：继续完善 Agent 能力目录；扩展更多结构化卡片；沉淀更多可复用测试数据；把监控面板从“定位问题”进一步推进到“辅助决策”。

#### Slide 16 - Closing

- **Closing impact**: 用一句话重申“从 Demo 到工程体系”的转变；背景线框从散点逐步闭合成回路。
- **Layout**: Full-bleed closing blueprint background + central takeaway.
- **Core message**: 这套 Agent 子系统已经具备长期运行、持续扩展、风险治理、观测运维和回归验证的工程化落地能力。
- **Content**: 我们做的不是一个会聊天的功能；我们做的是一套能在真实业务系统里长期运行、持续扩展，并且可以被管理和优化的 Agent 子系统。

---

## X. Speaker Notes Requirements

- **Total duration**: 12-15 分钟。
- **Notes style**: 正式但口语化；每页先讲结论，再讲 2-3 条证据。
- **File naming**: `01_cover.md` -> `16_closing.md`，由 `notes/total.md` 拆分。
- **Animation narration**: 每页 notes 包含“动画节奏提示”，与 `animations.json` 的对象 reveal 顺序一致。

---

## XI. Technical Constraints Reminder

1. viewBox: `0 0 1280 720`
2. 背景使用 `<rect>`；文字换行使用 `<tspan>`。
3. 禁用 `<foreignObject>`、`<style>`、`class`、`textPath`、`animate*`、`script`。
4. 透明度使用 `fill-opacity` / `stroke-opacity`；禁止 `rgba()`。
5. 图标统一 `chunk-filled`；禁止混用图标风格库。
6. 公式 PNG 使用 `preserveAspectRatio="xMidYMid meet"`，不得裁切。
