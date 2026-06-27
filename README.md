<p align="center">
  <h1 align="center">🎓 学生信息管理系统</h1>
  <p align="center">基于 FastAPI + SQLAlchemy 的 MVC 架构学生管理系统，集成 AI 大模型能力</p>
</p>

---

## 📋 项目简介

学生信息管理系统是一个功能完善的学生信息管理平台，涵盖学生基本信息、考核成绩、就业信息、班级管理、教师管理和统计分析等核心模块。当前版本已内置 **JWT + RBAC** 登录认证体系，提供登录态持久化、菜单/接口权限控制、系统用户/角色/权限管理；同时集成 **DeepSeek 大模型**和**阿里云通义万相**，提供 AI 智能评价、多轮对话、文生图、天气/地址解析、智能邮件助手以及 NL2SQL 智能问数等能力，并配套完整的 **Vue 3 前端工作台**。

### 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.x |
| ORM | SQLAlchemy |
| 数据校验 | Pydantic |
| 认证鉴权 | JWT（Bearer Token）+ RBAC |
| 数据库 | MySQL 5.7+ / 8.0 |
| 数据库驱动 | PyMySQL |
| 服务器 | Uvicorn |
| AI / LLM | DeepSeek V4 Flash、阿里云通义万相 (DashScope) |
| AI SDK | OpenAI SDK、DashScope SDK |
| 第三方接口 | 腾讯地图（天气查询 / 地理编码）、QQ 邮箱 SMTP |
| 文件处理 | openpyxl（Excel 读写）、python-multipart（文件上传） |
| SQL 工具 | sqlparse（NL2SQL 生成 SQL 格式化） |
| 前端 | Vue 3 + Vite + Vue Router + highlight.js（推荐） |
| 前端（静态版） | 原生 HTML + CSS + JavaScript（轻量调试面板） |
| 语言 | Python 3.10+ |

---

## 🏗️ 项目架构（MVC）

```
┌─────────────────────────────────────────────────┐
│                   main.py                       │
│              (应用入口 & 路由注册)                 │
├──────────┬──────────┬──────────────┬────────────┤
│  API/    │ service/ │    DAO/      │  model/    │
│Controller│  业务逻辑 │  数据访问     │  ORM模型   │
│ (薄层)    │  Service │   (纯查询)    │ (纯结构)   │
├──────────┴──────────┴──────────────┴────────────┤
│                  scheme/                        │
│       Pydantic 校验 & 统一响应 (View层)          │
├─────────────────────────────────────────────────┤
│         util/        │        LLM/              │
│  日志 / 邮件 等工具   │  AI 大模型 (DeepSeek+万相) │
├──────────────────────┴──────────────────────────┤
│                database.py                      │
│           数据库连接 & 会话管理                    │
├──────────────────────┬──────────────────────────┤
│     frontend-vue/    │       frontend/          │
│   Vue 3 SPA (推荐)   │  纯静态调试页（无鉴权）   │
└──────────────────────┴──────────────────────────┘
```

### 目录结构

```
├── main.py              # 应用入口，路由注册，全局异常处理，生命周期管理
├── database.py          # 数据库引擎、会话工厂、建表初始化
├── config.py            # 集中加载 .env 配置（数据库 / 各类密钥）
├── requirements.txt     # Python 依赖清单
├── API/                 # Controller 层 — HTTP 请求/响应处理
│   ├── auth_api.py                        # 登录 / 当前用户 / 修改密码
│   ├── system_api.py                      # 系统用户 / 角色 / 权限管理（仅 admin 可访问）
│   ├── student_api.py                     # 学生管理接口
│   ├── score_api.py                       # 成绩管理接口
│   ├── class_api.py                       # 班级管理接口
│   ├── employment_api.py                  # 就业管理接口
│   ├── teacher_information_API_Router.py  # 教师管理接口（含单个新增 / Excel 导入）
│   ├── statistical.py                     # 统计分析接口
│   ├── work_api.py                        # AI 作业 + 多轮对话 + 邮件模块接口
│   └── nl2sql_api.py                      # NL2SQL 智能问数接口
├── service/             # Service 层 — 业务逻辑
│   ├── auth_service.py                     # 登录、改密、用户/角色/权限管理
│   ├── student_service.py
│   ├── score_service.py                    # 含成绩批量导入/模板构建
│   ├── class_service.py
│   ├── employment_service.py
│   ├── teacher_service.py                 # 含 Excel/CSV 解析导入、模板生成
│   ├── statistical_service.py
│   ├── work_service.py                    # AI 服务（评价/对话/文生图/天气/地址）
│   └── nl2sql_service.py                  # 自然语言转 SQL、Schema 管理与查询执行
├── DAO/                 # 数据访问层 — 纯数据库操作
│   ├── auth_dao.py                         # RBAC 用户/角色/权限读写
│   ├── student_dao.py
│   ├── score_dao.py
│   ├── class_dao.py
│   ├── employment_dao.py
│   ├── teacher_information_CRUD.py
│   ├── statistical.py
│   ├── talk_dao.py                         # 多轮对话会话/消息持久化
│   └── nl2sql_dao.py                       # NL2SQL 会话、消息与缓存记录持久化
├── model/               # Model 层 — SQLAlchemy ORM 定义
│   ├── Auth.py                             # sys_user / sys_role / sys_permission 等 RBAC 模型
│   ├── Student.py
│   ├── Score.py
│   ├── Class.py
│   ├── Employment.py
│   ├── Teacher.py
│   ├── Talk.py                             # 会话表 + 消息表
│   └── NL2SQL.py                           # NL2SQL 会话、消息与缓存表
├── scheme/              # View 层 — Pydantic 校验 & 统一响应
│   ├── response_scheme.py                 # 统一 API 响应格式
│   ├── auth_scheme.py                     # 登录 / 系统用户 / 角色相关请求模型
│   ├── student_scheme.py
│   ├── schema_score.py
│   ├── class_scheme.py
│   ├── employment_scheme.py
│   ├── teacher_scheme.py
│   └── statistical_request.py
├── util/                # 工具层 — 跨模块通用能力
│   ├── auth.py                            # 密码哈希、JWT 生成与校验
│   ├── rbac.py                            # 当前用户解析、角色/权限校验依赖
│   ├── log.py                             # 日志系统（应用日志 + 请求访问日志）
│   └── email.py                           # 邮件内容生成（大模型）与 SMTP 发送
├── LLM/                 # AI 大模型集成
│   ├── ds_llm.py                          # DeepSeek 调用示例
│   └── ds_llm.ipynb                       # Jupyter Notebook 交互示例
├── frontend/            # 纯静态调试页（无登录态 / 不含 RBAC）
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── frontend-vue/         # Vue 3 前端（推荐，需构建运行）
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/index.js
│       ├── api/index.js
│       ├── utils/helpers.js
│       ├── assets/styles.css
│       ├── components/
│       │   ├── Sidebar.vue
│       │   ├── TopBar.vue
│       │   ├── ResultBadge.vue
│       │   └── DataTable.vue
│       └── views/
│           ├── LoginView.vue
│           ├── SystemView.vue
│           ├── StudentView.vue
│           ├── ScoreView.vue
│           ├── EmploymentView.vue
│           ├── ClassView.vue
│           ├── TeacherView.vue
│           ├── StatisticsView.vue
│           ├── WorkView.vue
│           ├── EmailView.vue
│           └── NL2SQLView.vue
└── logs/                # 运行日志（自动生成）
    ├── app.log                            # 全量应用日志
    └── error.log                          # 错误日志
```

### 分层职责

| 层 | 职责 | 不允许 |
|----|------|--------|
| **API** (Controller) | 接收请求、调用 Service、返回 HTTP 响应 | 业务逻辑、直接操作数据库 |
| **Service** (业务逻辑) | 业务校验、流程编排、调用 DAO / AI 模型 | HTTP 相关操作 |
| **DAO** (数据访问) | 纯数据库 CRUD、查询构建 | 业务规则、HTTP 操作 |
| **Model** (数据模型) | 表结构定义、字段映射 | 业务逻辑、基础设施代码 |
| **Scheme** (视图) | 请求/响应格式校验、统一响应结构 | 数据库操作 |
| **Util** (工具) | 日志、邮件、Excel 等跨模块通用能力 | 业务规则 |
| **LLM** (AI 集成) | 大模型调用、Prompt 工程、AI 服务封装 | 业务逻辑、数据库操作 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MySQL 5.7+ / 8.0
- pip

### 安装步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd student_-management_-system_code

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建数据库
# 登录 MySQL 执行：
# CREATE DATABASE student_management_system DEFAULT CHARACTER SET utf8mb4;

# 5. 配置环境变量（数据库 / API Key 等全部集中在 .env）
# 复制模板并填入真实值（.env 已被 .gitignore 忽略，不会提交）
cp .env.example .env       # Windows 用 copy .env.example .env
# 然后编辑 .env，填入数据库密码、DeepSeek/DashScope/腾讯地图等密钥

# 6. 启动服务
python main.py
# 服务将在 http://localhost:8088 启动

# 7. 访问 API 文档
# Swagger UI: http://localhost:8088/docs
# ReDoc:      http://localhost:8088/redoc
```

### 前端控制台

项目提供两套前端，推荐使用 Vue 3 版本体验完整登录鉴权、RBAC 菜单控制、系统管理和 NL2SQL 等能力；纯静态版本适合作为轻量调试面板：

#### Vue 3 版本（推荐）— `frontend-vue/`

基于 **Vue 3 + Vite + Vue Router**，支持登录鉴权、Bearer Token 持久化、路由守卫、按权限动态显示菜单、系统管理页、SQL 高亮和全局浅色 / 深色主题切换：

```bash
cd frontend-vue

# 安装依赖（仅首次）
npm install

# 启动开发服务器 → http://localhost:3000
npm run dev

# 生产构建 → dist/
npm run build
```

- 页面默认请求 `http://localhost:8088`，右上角 `API Endpoint` 可切换到其他后端地址；
- 左侧导航通过 Vue Router 管理，覆盖登录、学生、成绩、就业、班级、教师、统计、AI 作业、邮件、NL2SQL 和系统管理等模块；
- 支持 Bearer Token 持久化、启动时自动调用 `/auth/me` 恢复登录态、未登录跳转 `/login`、无菜单权限自动重定向；
- `SystemView.vue` 提供系统用户、角色、权限分配管理，且仅 `admin` 角色且拥有 `system:page` 菜单权限的账号可见；
- 支持全局浅色 / 深色主题切换，主题状态和子功能选择使用 `localStorage` 记忆；
- NL2SQL 页面使用 `highlight.js` 高亮生成 SQL；
- AI 作业多轮对话与 NL2SQL 默认绑定当前登录用户，无需手动输入 user_id；
- 组件懒加载，首屏仅加载当前模块。

#### 静态版本 — `frontend/`

纯 HTML + CSS + 原生 JS，无需任何构建工具，适合作为轻量调试面板：

- 直接用浏览器打开 `frontend/index.html` 即可使用；
- 页面右上角「接口地址」默认指向 `http://localhost:8088`，可随时修改；
- 覆盖学生、成绩、就业、班级、教师、统计、AI 作业、邮件等模块的基础调用；
- **不包含登录页、Bearer Token 持久化、路由守卫、系统管理页和 NL2SQL 页面**，这些能力请使用 `frontend-vue/`；
- 后端需开启 CORS（项目默认已放开），前端才能正常跨域调用接口。

### Docker 部署

```bash
# 构建镜像
docker build -t student-management .

# 运行容器
docker run -d -p 8088:8088 \
  -e DB_HOST=host.docker.internal \
  -e DB_USER=root \
  -e DB_PASSWORD=你的数据库密码 \
  -e DB_NAME=student_management_system \
  --name student-mgmt \
  student-management

# 访问
# http://localhost:8088/docs
```

---

## 📡 API 模块概览

| 模块 | 前缀 | 标签 | 功能 |
|------|------|------|------|
| 登录认证 | `/auth` | 登录认证 | 账号登录、获取当前用户、当前用户修改密码 |
| 系统管理 | `/system` | 系统管理 | 用户管理、角色管理、权限目录查询（仅 admin 可访问） |
| 学生管理 | `/student` | 学生基本信息管理 | CRUD、逻辑删除/恢复、分页查询 |
| 成绩管理 | `/score` | 学生考核成绩管理 | 单个/批量添加、修改、查询、删除、Excel 批量导入 |
| 就业管理 | `/Employment` | 学生就业信息管理 | CRUD、逻辑删除/恢复、物理删除 |
| 班级管理 | `/class` | 班级管理 | 新增/修改、删除、分页查询 |
| 教师管理 | (根路径) | 教师管理 | 单个新增、Excel/CSV 批量导入、模板下载、分页多条件搜索、更新 |
| 统计分析 | `/statistics` | 统计分析模块 | 年龄统计、成绩分析、薪资排行、就业时长 |
| AI 作业模块 | `/work` | 作业模块 | AI 智能评价、文生图、多轮记忆对话、天气查询、地址解析 |
| 邮件管理 | `/email` | 邮件管理 | 大模型生成邮件内容、确认后发送 |
| NL2SQL 智能问数 | `/nl2sql` | NL2SQL智能问数 | 自然语言转 SQL、表结构概览、查询历史记录 |

---

## 🤖 AI 模块说明

### 智能学生评价 (`POST /work/evaluation`)

根据学生成绩和性别，使用 **DeepSeek V4 Flash** 大模型生成个性化的智能评语，支持四种评价风格（`style` 参数直接传中文）：

| 风格 | 参数值 | 说明 |
|------|--------|------|
| 幽默 | `幽默` | 以轻松幽默的方式评价学生 |
| 严肃 | `严肃` | 以严谨正式的口吻评价学生 |
| 激励 | `激励` | 以鼓励激励的方式评价学生 |
| 批判 | `批判` | 以批判鞭策的方式评价学生 |

### 文生图 (`POST /work/image`)

调用**阿里云通义万相 (qwen-image-2.0-pro)** 模型，根据文本描述生成图片。

### 多轮记忆对话

基于 **DeepSeek V4 Flash** 实现的多轮对话，会话和消息全部持久化到 MySQL，支持多用户、多会话管理。当前后端会以**当前登录用户**作为会话归属，Vue 前端无需手动输入 user_id：

- `GET /work/talks/sessions` — 获取用户的所有历史会话（按更新时间倒序）
- `POST /work/talks/sessions` — 创建新会话
- `DELETE /work/talks/sessions/{session_id}` — 逻辑删除指定会话
- `GET /work/talks/{session_id}/messages` — 获取指定会话的全部历史消息
- `POST /work/talks` — 发送消息（传入 `session_id`、`user_id`、`prompt`），大模型携带历史上下文回复
- `POST /work/talks/clear` — 清空指定会话的全部消息（保留会话本身）

### 天气查询 / 地址解析（腾讯地图）

- `GET /work/weather` — 天气查询，`location`（经纬度）或 `adcode`（行政区划编码）二选一，`weather_type` 支持 `now` 实时 / `future` 多日 / `hours` 逐时
- `GET /work/geocoder` — 把文本地址解析为经纬度、结构化地址与行政区划编码

### 智能邮件助手（`/email`）

两步式邮件流程：先让大模型生成内容，用户确认/编辑后再发送。

- `POST /email/generate` — 一句话需求 → 大模型生成邮件主题与正文（仅返回内容，不发送）
- `POST /email/send` — 发送用户确认后的邮件（通过 QQ 邮箱 SMTP）

### NL2SQL 智能问数（`/nl2sql`）

基于 **DeepSeek V4 Flash** 将自然语言问题转换为可执行 SQL，并返回查询结果、生成 SQL、耗时与缓存状态；查询会话与历史记录持久化到 MySQL。当前查询默认绑定当前登录用户，前端无需手动输入 user_id。

- `POST /nl2sql/query` — 提交自然语言问题，自动生成 SQL 并执行查询
- `GET /nl2sql/schema` — 获取可查询数据库表结构、字段说明、JOIN 关系与聚合口径
- `GET /nl2sql/sessions` — 获取指定用户的历史查询会话和消息记录

---

## 🔐 认证与 RBAC

当前版本已接入基于 **Bearer Token** 的登录认证与 **RBAC** 权限模型：

- 后端通过 `Authorization: Bearer <token>` 识别当前用户；
- `util/auth.py` 负责密码强度校验、PBKDF2-SHA256 密码哈希、JWT 生成与校验；
- `util/rbac.py` 提供 `get_current_user`、角色校验、权限校验依赖；
- `API/system_api.py` 整体要求 `admin` 角色，同时细分到用户管理、角色管理、权限分配等接口权限；
- 业务模块接口已按 `student:*`、`score:*`、`employment:*`、`class:*`、`teacher:*`、`statistics:view`、`work:use`、`email:send`、`nl2sql:use` 等权限码接入校验；
- Vue 前端会在启动时通过 `/auth/me` 自动恢复登录态，并基于返回的 `menus / permissions / roles` 控制路由访问与菜单显示。

当前认证相关接口：

- `POST /auth/login` — 账号密码登录，返回 token、过期时间和当前用户信息
- `GET /auth/me` — 获取当前登录用户信息、角色、权限与菜单
- `POST /auth/change-password` — 当前登录用户修改密码
- `GET /system/users` / `POST /system/users` / `PATCH /system/users/{user_id}` — 系统用户管理
- `POST /system/users/{user_id}/reset-password` — 重置用户密码
- `POST /system/users/{user_id}/assign-roles` — 为用户分配角色
- `GET /system/roles` / `POST /system/roles` / `PATCH /system/roles/{role_id}` — 系统角色管理
- `POST /system/roles/{role_id}/assign-permissions` — 为角色分配权限
- `GET /system/permissions` — 查询权限目录

> 注意：仓库当前只保留了 RBAC 模型与接口实现，**未包含初始化 RBAC 默认数据的 SQL 文件**。如需登录与系统管理能力，需要先在数据库中准备 `sys_user / sys_role / sys_permission / sys_user_role / sys_role_permission` 数据。

## 👨‍🏫 教师批量导入

教师模块除单条新增外，提供更贴合教务实际的 **Excel/CSV 批量导入**：

1. **下载模板** — `GET /teachers/import/template` 返回带中文表头与示例行的标准 `.xlsx` 模板；
2. **填表** — 按列填写（姓名、性别、出生日期、联系电话、邮箱、职务、所带班级ID、入职日期；性别只填「男 / 女」）；
3. **上传导入** — `POST /teachers/import` 上传文件，后端逐行校验：**合格的入库、不合格的跳过**，并返回成功/失败条数与每个失败行的具体原因。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/teacher` | POST | 新增单个教师（表单提交一位老师） |
| `/teachers/import/template` | GET | 下载导入模板（.xlsx） |
| `/teachers/import` | POST | 上传 Excel/CSV 批量导入 |
| `/teachers` | POST | （保留）JSON 数组批量创建，仅作兼容 |

---

## 📊 成绩批量导入

成绩模块同样支持 **Excel/CSV 批量导入**，流程与教师导入一致：

1. **下载模板** — `GET /score/import/template` 返回带中文表头的标准 `.xlsx` 模板；
2. **填表** — 按列填写（学号、学生姓名、科目、成绩、考试日期等）；
3. **上传导入** — `POST /score/import` 上传文件，逐行校验后入库，返回成功/失败条数与失败原因。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/score/import/template` | GET | 下载导入模板（.xlsx） |
| `/score/import` | POST | 上传 Excel/CSV 批量导入 |

---

## 📦 API 响应格式

所有接口统一返回以下格式（字段为 `code` / `msg` / `data` / `total`）：

```json
// 普通响应
{
  "code": 200,
  "msg": "success",
  "data": { ... },
  "total": null
}

// 分页响应
{
  "code": 200,
  "msg": "success",
  "data": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

> 失败时同样返回该结构：`code` 为对应状态码，`msg` 为错误提示，`data` 在参数校验失败时会带上具体出错字段。

---

## 🔧 配置说明

所有敏感配置（数据库连接、各类 API Key、邮箱授权码）统一放在项目根目录的 `.env` 文件中，由 `config.py` 集中加载，源码里不再硬编码任何密钥。

参照 `.env.example` 复制一份 `.env` 并填入真实值：

```bash
# 大模型 DeepSeek
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 通义万相 DashScope（文生图）
DASHSCOPE_API_KEY=你的DashScope密钥

# 腾讯地图（天气查询 / 地理编码）
TENCENT_MAP_KEY=你的腾讯地图密钥

# QQ 邮箱 SMTP
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SENDER_EMAIL=你的发件邮箱@qq.com
SMTP_AUTH_CODE=你的邮箱SMTP授权码
DEFAULT_RECEIVER=默认收件邮箱@qq.com

# 数据库 MySQL
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_HOST=localhost
DB_PORT=3306
DB_NAME=student_management_system
DB_READONLY_USER=你的只读用户
DB_READONLY_PASSWORD=你的只读用户密码

# 登录认证 / RBAC
AUTH_SECRET_KEY=请改成一个长度足够且随机的密钥
AUTH_TOKEN_EXPIRE_MINUTES=720
AUTH_PBKDF2_ITERATIONS=600000
```

> `.env` 已被 `.gitignore` 忽略，不会提交到仓库；团队协作时只需共享 `.env.example` 模板。

服务端口在 `main.py` 中配置（默认 `8088`）。

---

## 📝 开发说明

- 数据表在应用启动时通过 `init_db()` 自动创建；其中 RBAC 相关模型也会自动建表，但默认用户/角色/权限数据需要你自行初始化
- 所有删除操作均为逻辑删除（`is_deleted` 字段），就业模块额外支持物理删除
- 登录认证采用 Bearer Token；密码使用 PBKDF2-SHA256 哈希，JWT 过期时间与哈希迭代次数可通过 `.env` 配置
- Vue 前端当前已经支持登录页、登录态恢复、菜单级权限控制、系统管理页、当前用户展示与退出登录
- `frontend-vue` 通过 `src/api/index.js` 统一管理 API base URL 与 Bearer Token；如需改成完全相对路径部署，可再按需完善 `vite.config.js` 代理
- 多轮对话的会话与消息已持久化到 MySQL，不会因服务重启丢失；历史上下文按会话 ID 自动加载
- NL2SQL 智能问数的查询会话、消息和缓存记录已持久化到 MySQL，前端可查看历史记录并高亮展示生成 SQL
- 教师批量导入采用「逐行校验、部分成功」策略：合格数据入库，失败数据跳过并返回原因，不会因个别行出错而整体失败
- 日志由 `util/log.py` 统一管理，应用日志写入 `logs/app.log`、错误日志写入 `logs/error.log`，并接管 uvicorn 日志与请求访问日志
- 前端提供两套实现：`frontend-vue/`（Vue 3，推荐，支持登录鉴权、RBAC 菜单控制、系统管理、浅色/深色主题与 NL2SQL SQL 高亮）和 `frontend/`（纯静态调试页，不含登录态 / RBAC / 系统管理 / NL2SQL 页面）
- DeepSeek、DashScope、腾讯地图等密钥请在 `.env` 中替换为自己的有效密钥

---

## 📄 License

本项目仅用于学习目的。
