# 学生管理系统 — Agent 接入改造设计文档（AI 执行规范）

> 本文档不是讲概念，而是给 AI 编码时直接执行的接入改造规范。
> 目标是让 AI 在阅读本文档后，能够基于当前项目 `D:\student_-management_-system_code` 的现有结构，精准设计并实现二阶段所需的 Agent 系统。
>
> 本文档重点解决 6 个问题：
>
> 1. 当前项目适不适合接入 Agent
> 2. 应该新增哪些目录和文件
> 3. 现有模块哪些要复用，哪些要包装成工具
> 4. Agent 请求链路应该怎么走
> 5. 第一版 Agent 应该先实现哪些功能
> 6. AI 编码时必须遵守哪些边界和禁止事项

---

## 一、适用范围

本文档只适用于当前项目：

`D:\student_-management_-system_code`

并默认以下前提已经成立：

- 项目已有 `FastAPI + SQLAlchemy + Pydantic` 主体架构
- 项目已有 `API / service / DAO / model / scheme` 分层
- 项目已有 `RAG / NL2SQL / 多轮对话 / 日志 / 权限` 等基础能力
- 本次改造目标是“在不破坏一阶段业务主干的前提下，引入二阶段 Agent 系统”

如果 AI 编码时脱离当前项目实际结构，直接照搬通用 Agent 脚手架，视为不符合本文档要求。

---

## 二、当前项目结构判断

AI 在开始编码前，必须先理解当前项目不是空白工程，而是已经具备较强基础设施的现有系统。

当前项目的关键结构如下：

```text
D:\student_-management_-system_code
├── main.py
├── API/
├── service/
├── DAO/
├── model/
├── scheme/
├── util/
├── LLM/
├── NL2SQL/
├── RAG/
├── frontend/
├── frontend-vue/
└── docs/
```

### 已存在且可直接复用的能力

1. `API/`
已有成熟路由层，可继续挂接新 Agent 路由。

2. `service/`
已有学生、成绩、班级、就业、统计、作业、NL2SQL 等服务层逻辑。

3. `DAO/`
已有稳定的数据访问层。

4. `model/Talk.py`
已有会话表与消息表，可直接为 Agent 会话历史提供基础。

5. `DAO/talk_dao.py` + `service/work_service.py`
已有多轮对话缓存、摘要、风格偏好能力，可作为 Agent 记忆能力的重要参考或部分复用对象。

6. `RAG/`
已有完整检索增强问答子系统，可作为 Agent 的知识检索工具。

7. `NL2SQL/` + `service/nl2sql_service.py`
已有自然语言问数能力，可作为 Agent 的“数据查询工具”。

8. `util/rbac.py`
已有权限体系，可约束 Agent 能调用哪些业务能力。

### 核心判断结论

当前项目：

- **不适合整体重构为全新 Agent 架构工程**
- **适合在现有主工程内新增一个 Agent 子系统进行局部嫁接**

因此，AI 编码时必须采用：

**“保留原系统主结构 + 新增 agent_system 子系统”的方案。**

---

## 三、改造总原则

AI 在本项目中接入 Agent 时，必须遵守以下总原则：

1. 不重构现有 `API / service / DAO / model / scheme` 主骨架。
2. 不把 Agent 逻辑直接塞进现有某个 `service/*.py` 大文件里。
3. 不让 Agent 直接跨层随意调用 `DAO` 或底层 RAG 细节。
4. 现有 `RAG / NL2SQL / 业务 service` 必须先包装成 Agent 工具，再由 Agent 调用。
5. 第一版 Agent 必须做成“受控 Agent”，而不是“全自动万能 Agent”。
6. 高风险业务动作默认不允许自动执行；后续如需扩展，必须预留 HITL（人工确认）位置。

---

## 四、推荐新增目录结构

AI 在当前项目中接入 Agent 时，必须新增如下子系统目录：

```text
D:\student_-management_-system_code
├── agent_system/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── agent_api.py
│   ├── service/
│   │   ├── __init__.py
│   │   └── agent_service.py
│   ├── planner/
│   │   ├── __init__.py
│   │   ├── task_planner.py
│   │   ├── intent_classifier.py
│   │   └── plan_schema.py
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── agent_executor.py
│   │   ├── step_runner.py
│   │   └── state_manager.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── academic_agent.py
│   │   ├── companion_agent.py
│   │   └── supervisor_agent.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── score_tool.py
│   │   ├── student_tool.py
│   │   ├── class_tool.py
│   │   ├── employment_tool.py
│   │   ├── statistics_tool.py
│   │   ├── nl2sql_tool.py
│   │   ├── rag_tool.py
│   │   └── work_tool.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── conversation_memory.py
│   │   ├── working_memory.py
│   │   └── summary_memory.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── persona_prompt.py
│   │   ├── planner_prompt.py
│   │   ├── academic_prompt.py
│   │   └── companion_prompt.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── intent_parser.py
│   │   ├── action_parser.py
│   │   └── response_parser.py
│   ├── hitl/
│   │   ├── __init__.py
│   │   ├── human_review.py
│   │   └── escalation_rules.py
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── tracer.py
│   │   └── retry_handler.py
│   └── schemas/
│       ├── __init__.py
│       ├── agent_request.py
│       ├── agent_response.py
│       └── task_state.py
```

### 为什么必须单独建 `agent_system/`

原因如下：

1. 可以避免污染现有主业务目录。
2. 可以让 Agent 系统独立演进，不影响一阶段功能。
3. 可以清晰区分“原业务服务”和“AI 编排系统”。
4. 方便后续做日志、监控、审批、记忆等增强能力。

禁止 AI 采用以下错误做法：

- 在 `service/work_service.py` 中继续堆所有 Agent 逻辑
- 在 `API/work_api.py` 或 `API/student_api.py` 中直接写 Planner / Tool / Memory
- 在根目录再平铺十几个 `agent_*.py` 文件

---

## 五、现有模块复用与包装规则

AI 必须先复用已有模块，再决定新写能力。

### 1. 必须包装成工具的现有模块

#### `service/score_service.py` → `agent_system/tools/score_tool.py`

用途：

- 查询成绩
- 查询某学生某科目表现
- 查询成绩趋势

适用场景：

- “我想查成绩”
- “我数学怎么样”
- “我这学期成绩变化大吗”

#### `service/student_service.py` → `agent_system/tools/student_tool.py`

用途：

- 查询学生基本信息
- 获取学生身份信息用于上下文补全

#### `service/class_service.py` → `agent_system/tools/class_tool.py`

用途：

- 查询班级信息
- 获取班级维度背景数据

#### `service/employment_service.py` → `agent_system/tools/employment_tool.py`

用途：

- 查询就业信息
- 就业建议相关场景的数据支持

#### `service/statistical_service.py` → `agent_system/tools/statistics_tool.py`

用途：

- 获取统计分析结果
- 为学业分析、班级分析提供聚合数据

#### `service/nl2sql_service.py` → `agent_system/tools/nl2sql_tool.py`

用途：

- 开放式数据库问数
- Agent 无法通过固定 service 解决时，走自然语言问数

重要要求：

- Agent 不能直接散着调用 `NL2SQL/` 底层模块
- 只能通过工具层调用 `service/nl2sql_service.query()` 或其封装接口

#### `RAG/` → `agent_system/tools/rag_tool.py`

用途：

- 制度问答
- 系统使用说明
- 学习资料问答
- 文档型知识补充

重要要求：

- Agent 不能直接 import `RAG/retrieval.py`、`RAG/generation.py` 等底层细节来拼流程
- 必须通过统一 `rag_tool` 或 `rag_adapter` 调用现有 `RAG` 子系统

#### `service/work_service.py` → `agent_system/tools/work_tool.py`

用途：

- 复用已有多轮对话基础能力
- 复用部分文生内容能力
- 复用天气 / 地址等外围 AI 功能（如业务需要）

### 2. 可以复用的数据结构基础

#### `model/Talk.py`

可复用点：

- `TalkSession`
- `TalkMessage`

建议：

- 第一版 Agent 可先复用现有会话表结构
- 若后续 Agent 任务状态越来越复杂，再新增独立 Agent 任务表

#### `DAO/talk_dao.py`

可复用点：

- 会话查询
- 消息查询
- 会话写入
- 摘要更新

#### `service/work_service.py`

可参考或部分复用点：

- 会话缓存
- 摘要生成
- 风格识别
- 多轮消息裁剪逻辑

---

## 六、当前项目推荐的 Agent 角色

AI 第一版实现时，必须优先做下面两个角色中的一个或两个。

### 角色 1：学业导师 Agent

推荐优先级：最高

角色定位：

- 温和
- 鼓励型
- 擅长学业分析
- 能解释成绩与学习问题

必须支持的能力：

1. 成绩查询
2. 学业表现分析
3. 学习建议生成
4. 基础知识问答
5. 诗词鉴赏或鼓励型表达

### 角色 2：陪伴班主任 Agent

推荐优先级：次高

角色定位：

- 有共情能力
- 会温和安慰
- 不越界
- 不做诊断

必须支持的能力：

1. 压力安慰
2. 学习焦虑共情
3. 人际烦恼基础陪伴
4. 适时引导联系老师 / 家长 / 专业人员

重要边界：

- 不做医疗诊断
- 不做心理治疗承诺
- 不输出危险建议

### 第一版选型要求

如果时间有限，AI 必须先做：

**知识问答机器人 + 学业导师 Agent**

不要第一版就做多角色协作系统。

---

## 七、第一版 Agent 功能范围（强制）

AI 在第一版实现中，必须至少完成下面 5 个功能：

1. `学生查询成绩`
2. `学生追问某科成绩或趋势`
3. `学生询问制度 / 课程 / 系统说明`
4. `学生请求学业建议`
5. `学生表达考试压力时，给出基础共情回应`

### 对应能力映射

| 用户意图 | 处理方式 |
|------|------|
| 查询成绩 | `score_tool` |
| 问成绩细节 / 追问 | `score_tool + memory` |
| 制度问答 | `rag_tool` |
| 开放式数据问题 | `nl2sql_tool` |
| 学习建议 | `academic_agent + score_tool + statistics_tool` |
| 情绪陪伴 | `companion_agent` |

禁止 AI 第一版就做：

- 自动发邮件
- 自动改数据库业务数据
- 多 Agent 协作编排
- 长链审批流
- 很重的长期画像系统

---

## 八、推荐新增接口

AI 在接入 Agent 时，建议最少新增以下接口：

### 1. `POST /agent/chat`

作用：

- Agent 主聊天入口
- 支持普通问答、知识问答、工具调用、陪伴对话

请求建议字段：

- `message`
- `session_id`
- `persona`
- `context`（可选）

### 2. `GET /agent/sessions`

作用：

- 获取当前用户的 Agent 会话列表

### 3. `GET /agent/sessions/{session_id}/messages`

作用：

- 获取某个会话的历史消息

### 4. `POST /agent/feedback`

作用：

- 记录用户对某次 Agent 回复的反馈

### 5. `GET /agent/personas`

作用：

- 返回当前系统支持的 Agent 角色列表

### 推荐挂载位置

- 新路由文件：`agent_system/api/agent_api.py`
- 在 [main.py](D:/student_-management_-system_code/main.py) 中注册：
  - `app.include_router(agent_router, prefix='/agent', tags=['智能Agent'])`

禁止把 Agent 路由挂到：

- `API/work_api.py`
- `API/student_api.py`
- `API/nl2sql_api.py`

原因：职责会混乱。

---

## 九、请求流转规范（强制执行）

AI 在实现 Agent 主链路时，必须按以下流程设计：

1. 前端请求进入 `agent_system/api/agent_api.py`
2. API 层只做参数校验和用户身份获取
3. 请求转交 `agent_system/service/agent_service.py`
4. `agent_service` 调用 `planner/intent_classifier.py` 识别意图
5. `planner/task_planner.py` 输出结构化计划
6. `executor/agent_executor.py` 执行计划
7. 执行过程中按需调用：
   - `tools/score_tool.py`
   - `tools/student_tool.py`
   - `tools/statistics_tool.py`
   - `tools/nl2sql_tool.py`
   - `tools/rag_tool.py`
8. 如果需要上下文，读取 `memory/` 中的对话或任务状态
9. 结果统一经过 `parsers/response_parser.py` 整理
10. 返回统一响应给前端

### 严禁的错误流转

禁止以下实现方式：

- `API -> LLM -> response`
- `API -> RAG -> response`
- `API -> score_service -> LLM -> response`
- `API -> tool -> response`

因为这些实现方式缺少：

- 意图识别
- 计划编排
- 统一记忆
- 角色控制
- 后续可扩展性

---

## 十、Planner 设计规范

AI 实现 Planner 时，必须把规划与执行分开。

### `intent_classifier.py` 必须做的事

负责识别以下至少 6 类意图：

1. `score_query`
2. `academic_advice`
3. `knowledge_qa`
4. `data_query`
5. `emotional_support`
6. `general_chat`

### `task_planner.py` 必须做的事

根据意图输出结构化计划，例如：

```python
class PlanStep(BaseModel):
    step_id: str
    action: str
    tool_name: str | None = None
    need_retrieval: bool = False
    need_memory: bool = True
    need_human_review: bool = False


class ExecutionPlan(BaseModel):
    intent: str
    persona: str
    goal: str
    steps: list[PlanStep]
```

### Planner 禁止事项

- 不直接调用工具
- 不直接返回最终答案
- 不返回难以解析的大段自然语言计划

---

## 十一、Executor 设计规范

AI 实现 Executor 时，必须让它只负责执行，不负责“重新思考整体策略”。

### `agent_executor.py` 职责

- 接收结构化计划
- 推进每一步
- 调用工具
- 读取记忆
- 合并结果
- 产出最终响应草稿

### `step_runner.py` 职责

- 根据不同 step 类型调用对应工具或子能力

### `state_manager.py` 职责

- 管理当前任务状态
- 记录中间结果
- 供多轮追问复用

### Executor 禁止事项

- 把所有逻辑写成一个 500 行函数
- 直接在执行器里重新判断用户到底想干什么
- 让执行器直接操作数据库底层表而不经过工具或 service

---

## 十二、Memory 设计规范

当前项目已经有多轮对话基础，AI 可以复用但不能无脑照搬。

### 推荐内存拆分

#### `conversation_memory.py`

保存：

- 用户问过什么
- AI 回过什么
- 最近若干轮上下文

#### `working_memory.py`

保存：

- 当前任务中间状态
- 当前已经调用过哪些工具
- 当前已经获取过哪些结果

#### `summary_memory.py`

保存：

- 会话摘要
- 用户风格偏好
- 长对话精简背景

### 可复用来源

- `model/Talk.py`
- `DAO/talk_dao.py`
- `service/work_service.py` 中的摘要、风格、缓存逻辑

### Memory 禁止事项

- 把工作状态和聊天历史完全混成一个列表
- 每个模块自己维护一份状态，导致状态分裂

---

## 十三、工具设计规范

AI 在当前项目里实现工具时，必须遵守下面规则：

1. 每个工具只做一件事。
2. 工具是 Agent 与现有业务系统之间的桥梁。
3. 工具优先调用现有 `service/` 层，不直接越过 service 去打 DAO。
4. 工具返回结果尽量结构化。
5. 工具异常必须可感知。

### 示例工具边界

#### `score_tool.py`

允许：

- 查询某学生成绩
- 查询某科成绩
- 查询最近几次成绩趋势

禁止：

- 在工具里直接写大段学业分析结论

#### `rag_tool.py`

允许：

- 根据问题获取 RAG 回答或知识上下文

禁止：

- 在工具里自己承担完整 Agent 角色回复逻辑

#### `nl2sql_tool.py`

允许：

- 将自然语言数据问题交给现有 `service/nl2sql_service.py`

禁止：

- 在工具里再重新实现一套 SQL 生成逻辑

---

## 十四、推荐前端接入方式

当前项目已有 `frontend-vue/`，AI 实现前端接入时，推荐：

1. 新增一个独立页面，如：
   - `AgentView.vue`
2. 在路由中新增：
   - `/agent`
3. 页面中至少支持：
   - 输入问题
   - 选择角色
   - 显示会话历史
   - 显示工具调用结果摘要（可选）
   - 显示来源依据（知识问答场景）

禁止：

- 直接在现有某个业务表单页里硬塞完整 Agent 界面

---

## 十五、推荐新增数据表（第二步实现）

第一版可以先复用 `talk_session` 和 `talk_message`。  
如果后续能力增强，再建议新增以下表：

1. `agent_task_log`
作用：记录每次 Agent 执行的计划、步骤、耗时、结果

2. `agent_feedback`
作用：记录用户满意度或反馈

3. `agent_persona_config`
作用：存放不同角色的设定和开关

### 第一版要求

AI 第一版不强制新增表，但必须预留扩展点。

---

## 十六、编码顺序规范（强制）

AI 在本项目中实现 Agent 时，推荐严格按下面顺序进行：

1. 新建 `agent_system/schemas/`
2. 新建 `agent_system/prompts/`
3. 新建 `agent_system/planner/`
4. 新建 `agent_system/tools/`
5. 新建 `agent_system/memory/`
6. 新建 `agent_system/executor/`
7. 新建 `agent_system/agents/`
8. 新建 `agent_system/service/agent_service.py`
9. 新建 `agent_system/api/agent_api.py`
10. 修改 [main.py](D:/student_-management_-system_code/main.py) 注册路由
11. 如有前端需求，再新增 `frontend-vue` 页面和路由

原因：

- 先把骨架和边界搭好
- 再接入现有能力
- 最后再挂入口

---

## 十七、AI 编码时的禁止事项

AI 在本项目里实现 Agent 时，禁止下面这些反模式：

1. 把 Agent 全写进 `service/work_service.py`。
2. 在 `API` 层直接调用 LLM 和工具。
3. 让 Agent 直接散着 import `RAG/` 底层函数拼流程。
4. 让 Agent 绕开现有 `service/` 直接访问 `DAO/`。
5. 把成绩查询、知识问答、陪伴对话、统计分析全塞进一个超长文件。
6. 没有意图分类和计划层，就直接进入工具调用。
7. 把自然语言大段文本当成执行计划在系统内部传递。
8. 第一版就实现自动写库、自动审批、自动通知等高风险动作。

---

## 十八、最小实现目标（MVP）

AI 第一版必须至少交付下面这些内容：

### 后端

1. `POST /agent/chat`
2. Agent 意图识别
3. 学业导师角色
4. 成绩查询工具
5. RAG 问答工具
6. 多轮会话基础记忆

### 前端

1. 一个 Agent 页面
2. 可发送消息
3. 可查看返回结果
4. 可查看历史会话（可简化）

### 体验层

1. 支持查询成绩
2. 支持知识问答
3. 支持学业建议
4. 支持基础共情回应

---

## 十九、最小伪代码模板

AI 可以按下面的最小骨架组织主流程：

```python
# agent_system/api/agent_api.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from util.rbac import get_current_user
from agent_system.schemas.agent_request import AgentChatRequest
from agent_system.service.agent_service import handle_agent_chat

agent_router = APIRouter()


@agent_router.post('/chat')
def chat(req: AgentChatRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_agent_chat(req=req, current_user=current_user, db=db)
```

```python
# agent_system/service/agent_service.py
from agent_system.planner.intent_classifier import classify_intent
from agent_system.planner.task_planner import build_plan
from agent_system.executor.agent_executor import run_plan


def handle_agent_chat(req, current_user, db):
    intent = classify_intent(req.message)
    plan = build_plan(message=req.message, persona=req.persona, intent=intent)
    result = run_plan(plan=plan, user=current_user, session_id=req.session_id, db=db)
    return result
```

```python
# agent_system/executor/agent_executor.py
from agent_system.tools.score_tool import query_student_score
from agent_system.tools.rag_tool import ask_knowledge_base


def run_plan(plan, user, session_id, db):
    context = {}
    for step in plan.steps:
        if step.tool_name == 'score_tool':
            context['score'] = query_student_score(user=user, question=plan.goal, db=db)
        elif step.tool_name == 'rag_tool':
            context['knowledge'] = ask_knowledge_base(question=plan.goal)
    return {
        'code': 200,
        'msg': 'ok',
        'data': context,
    }
```

---

## 二十、AI 自检清单

AI 在完成 Agent 接入前，必须自检：

- 是否保留了原项目主结构？
- 是否新增了 `agent_system/` 而不是污染原目录？
- 是否把现有能力先包装成工具再调用？
- 是否把 Planner / Executor / Tool / Memory 拆开了？
- 是否避免了 API 层直调 LLM？
- 是否第一版只做受控能力，而不是全自动高风险能力？
- 是否把 `main.py` 路由注册考虑进去？
- 是否为前端页面留出了独立入口？

如果任意一项不满足，先重构，再继续实现功能。

---

## 二十一、一句话执行原则

AI 在当前项目中接入 Agent 时，始终遵守一句话：

**不是把 Agent 塞进现有系统里，而是在现有系统上搭建一个可复用、可扩展、可受控的智能体子系统。**
