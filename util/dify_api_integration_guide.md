# Dify 对接本项目接口说明

> 更新时间：2026-06-08  
> 适用项目：学生信息管理系统（FastAPI，默认端口 `8088`）

---

## 1. 基础接入信息

### 1.1 服务基地址

本项目后端默认启动地址：

```text
http://localhost:8088
```

如果 Dify 和本项目不在同一运行环境中，请把 `localhost` 替换成 **Dify 实际可访问** 的主机/IP/域名。

---

### 1.2 统一响应格式

除个别文件下载接口外，接口统一返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {},
  "total": null
}
```

分页接口会多出：

```json
{
  "code": 200,
  "msg": "success",
  "data": [],
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

Dify 中建议优先取：

- 业务是否成功：`code == 200`
- 提示文案：`msg`
- 业务结果：`data`
- 分页总数：`total`

---

### 1.3 认证方式

除登录接口外，其余主接口都走 **Bearer Token**：

```http
Authorization: Bearer <token>
```

登录接口：

- **POST** `/auth/login`
- 请求体：

```json
{
  "username": "admin",
  "password": "你的密码"
}
```

成功后返回：

```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "token": "<jwt>",
    "token_type": "bearer",
    "expires_in": 43200,
    "user": {
      "id": 1,
      "username": "admin",
      "real_name": "管理员"
    }
  },
  "total": null
}
```

Dify 里建议这样接：

1. 第一个 HTTP 节点调用 `/auth/login`
2. 从返回体中提取 `data.token`
3. 后续所有节点统一加请求头：
   - `Authorization: Bearer {{token}}`
   - `Content-Type: application/json`

---

### 1.4 Dify 调用时的 4 种常见方式

#### A. GET + Query 参数

例如：

```text
GET /student/students?skip=0&limit=20
```

适合：查询、分页、统计。

#### B. POST/PUT/PATCH + JSON Body

例如：

```json
{
  "student_no": "S2024001",
  "class_id": 1,
  "student_name": "张三"
}
```

适合：新增、更新、登录、NL2SQL、会话创建等。

#### C. POST 但参数走 Query

本项目有少量接口虽然是 `POST`，但参数定义在函数入参中，因此应按 **Query 参数** 传递，例如：

- `POST /work/evaluation?student_id=1&style=幽默`
- `POST /work/image?prompt=一只在草地上奔跑的柯基`
- `POST /email/generate?prompt=给老师写一封请假邮件`

#### D. multipart/form-data 文件上传

适合导入接口：

- `POST /score/import`
- `POST /teachers/import`

如果 Dify 工作流不方便传文件，这两个接口建议暂时不接。

---

## 2. Dify 中优先推荐接入的接口

如果你只是想让 Dify 快速可用，优先接这几个：

1. `POST /auth/login` — 登录拿 token
2. `POST /nl2sql/query` — 智能问数
3. `GET /nl2sql/schema` — 获取可问表结构
4. `POST /work/evaluation` — 学生评价
5. `POST /work/talks` — AI 多轮对话
6. `GET /work/weather` — 天气查询
7. `GET /work/geocoder` — 地址解析
8. `POST /email/generate` — 生成邮件
9. `POST /email/send` — 发送邮件
10. `GET /statistics/stu_count` — 学生人数统计

---

## 3. 接口总表（按模块）

---

## 3.1 登录认证模块 `/auth`

| 功能 | 方法 | URL | 鉴权 | 参数位置 | 调用说明 |
|------|------|-----|------|----------|----------|
| 登录 | POST | `/auth/login` | 否 | JSON Body | 传 `username`、`password` |
| 获取当前用户 | GET | `/auth/me` | 是 | 无 | 返回当前登录用户、角色、权限、菜单 |
| 当前用户改密 | POST | `/auth/change-password` | 是 | JSON Body | 传 `old_password`、`new_password` |

### 登录请求体示例

```json
{
  "username": "admin",
  "password": "Admin@123456"
}
```

### 修改密码请求体示例

```json
{
  "old_password": "旧密码",
  "new_password": "新密码123"
}
```

---

## 3.2 系统管理模块 `/system`

> 整个模块要求：
>
> - 已登录
> - 具备 `admin` 角色
> - 再叠加对应的细分权限

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 分页查询用户 | GET | `/system/users` | Query | `skip` `limit` `username` `real_name` `status` |
| 创建用户 | POST | `/system/users` | JSON Body | 创建系统用户 |
| 更新用户 | PATCH | `/system/users/{user_id}` | Path + JSON Body | 更新姓名/手机号/邮箱/状态等 |
| 重置密码 | POST | `/system/users/{user_id}/reset-password` | Path + JSON Body | 重置用户密码 |
| 分配用户角色 | POST | `/system/users/{user_id}/assign-roles` | Path + JSON Body | 传角色 ID 列表 |
| 分页查询角色 | GET | `/system/roles` | Query | `skip` `limit` `role_name` `status` |
| 创建角色 | POST | `/system/roles` | JSON Body | 创建系统角色 |
| 更新角色 | PATCH | `/system/roles/{role_id}` | Path + JSON Body | 更新角色名称/状态/备注 |
| 分配角色权限 | POST | `/system/roles/{role_id}/assign-permissions` | Path + JSON Body | 传权限 ID 列表 |
| 查询权限目录 | GET | `/system/permissions` | Query | `module` `permission_type` 可选 |

### 创建用户请求体示例

```json
{
  "username": "dify_bot",
  "password": "StrongPass123",
  "real_name": "Dify服务账号",
  "phone": null,
  "email": null,
  "status": 1,
  "must_change_password": 0,
  "role_ids": [1]
}
```

### 重置密码请求体示例

```json
{
  "new_password": "NewPass123",
  "must_change_password": 0
}
```

### 分配用户角色请求体示例

```json
{
  "role_ids": [1, 2]
}
```

### 创建角色请求体示例

```json
{
  "role_code": "dify_operator",
  "role_name": "Dify操作员",
  "status": 1,
  "remark": "供 Dify 工作流调用"
}
```

### 分配角色权限请求体示例

```json
{
  "permission_ids": [1, 2, 3]
}
```

---

## 3.3 学生模块 `/student`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 创建学生 | POST | `/student/students` | JSON Body | 新增学生 |
| 分页查询全部学生 | GET | `/student/students` | Query | `skip` `limit` |
| 按 ID 查询 | GET | `/student/students/{student_id}` | Path | 查询单个学生 |
| 按学号查询 | GET | `/student/students/no/{student_no}` | Path | 查询单个学生 |
| 按班级查询 | GET | `/student/students/class/{class_id}` | Path + Query | `skip` `limit` |
| 更新学生 | PATCH | `/student/students/{student_id}` | Path + JSON Body | 部分更新 |
| 逻辑删除学生 | DELETE | `/student/students/{student_id}` | Path | 删除 |
| 恢复学生 | POST | `/student/students/{student_id}/restore` | Path | 恢复 |

### 创建学生请求体示例

```json
{
  "student_no": "S2024001",
  "class_id": 1,
  "student_name": "张三",
  "gender": "男",
  "age": 20,
  "native_place": "北京市",
  "graduate_school": "北京一中",
  "major": "计算机科学",
  "education": "本科",
  "admission_time": "2024-09-01",
  "graduate_time": "2028-06-30",
  "advisor_id": 1
}
```

### 更新学生请求体示例

```json
{
  "student_name": "张三（已更新）",
  "major": "软件工程"
}
```

---

## 3.4 成绩模块 `/score`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 新增单条成绩 | POST | `/score/add` | JSON Body | 新增一条成绩 |
| 批量新增成绩 | POST | `/score/batch_add` | JSON Body | Body 是数组 |
| 更新成绩 | PUT | `/score/update` | JSON Body | 按学号+考试次序更新 |
| 删除成绩 | POST | `/score/is_delete` | Query | `student_no` `exam_order` |
| 查询成绩 | GET | `/score/query` | Query | 支持分页、范围、排序 |
| 下载导入模板 | GET | `/score/import/template` | 无 | 返回 xlsx 文件 |
| 导入成绩 | POST | `/score/import` | multipart/form-data | 上传 Excel/CSV |

### 新增成绩请求体示例

```json
{
  "student_no": "S2024001",
  "exam_order": 1,
  "score": 88
}
```

### 批量新增成绩请求体示例

```json
[
  {
    "student_no": "S2024001",
    "exam_order": 1,
    "score": 88
  },
  {
    "student_no": "S2024002",
    "exam_order": 1,
    "score": 92
  }
]
```

### 成绩查询示例

```text
GET /score/query?page=1&page_size=10&student_no=S2024001&sort_score=desc
```

---

## 3.5 就业模块 `/Employment`

> 注意：这里的前缀是 **大写 E**，不是 `/employment`。

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 新建就业信息 | POST | `/Employment/employment_create` | JSON Body | 新建 |
| 按 ID 查询 | GET | `/Employment/employment_get/{emp_id}` | Path | 查询单条 |
| 分页查询 | GET | `/Employment/employment_list` | Query | `page` `size` `student_name` `class_id` `company_name` |
| 更新就业信息 | PUT | `/Employment/employment_update/{emp_id}` | Path + JSON Body | 更新 |
| 逻辑删除 | DELETE | `/Employment/employment_delete/{emp_id}` | Path | 删除 |
| 逻辑恢复 | PUT | `/Employment/employment_recover/{emp_id}` | Path | 恢复 |
| 物理删除 | DELETE | `/Employment/employment_hard/{emp_id}` | Path | 真删，不可恢复 |

### 新建就业信息请求体示例

```json
{
  "student_no": "S2024001",
  "student_name": "张三",
  "class_id": 1,
  "job_open_time": "2026-03-01",
  "offer_send_time": "2026-04-15",
  "company_name": "腾讯",
  "salary": 18000
}
```

### 更新就业信息请求体示例

```json
{
  "company_name": "阿里巴巴",
  "salary": 22000
}
```

---

## 3.6 班级模块 `/class`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 新增/修改班级 | POST | `/class/create_or_update_class` | JSON Body + Query | 不带 `id` 时新增，带 `id` 时修改 |
| 删除班级 | DELETE | `/class/del_class` | Query | `id` |
| 分页查询班级 | GET | `/class/get_class` | Query | `page` `limit` |
| 按 ID 查询班级 | GET | `/class/get_class/{id}` | Path | 查询单条 |

### 新增班级请求体示例

```json
{
  "class_code": "C2024A",
  "class_name": "2024级A班",
  "start_time": "2024-09-01T08:00:00"
}
```

### 修改班级调用方式示例

```text
POST /class/create_or_update_class?id=1
```

请求体：

```json
{
  "class_code": "C2024A",
  "class_name": "2024级A班（更新）",
  "start_time": "2024-09-01T08:00:00"
}
```

---

## 3.7 教师模块（无统一前缀）

> 这个模块没有像 `/teacher` 这样的公共前缀，接口直接挂在根路径。

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 按 ID 查询教师 | GET | `/teachers/{id}` | Path | 查询单条 |
| 分页/筛选教师 | GET | `/teachers` | Query | 支持 name/gender/title/class_id 等筛选 |
| 新增单个教师 | POST | `/teacher` | JSON Body | 推荐单条创建 |
| 批量创建教师 | POST | `/teachers` | JSON Body | Body 是数组，兼容接口 |
| 更新教师 | PUT | `/teachers/{id}` | Path + JSON Body | 更新 |
| 下载教师导入模板 | GET | `/teachers/import/template` | 无 | 返回 xlsx |
| 批量导入教师 | POST | `/teachers/import` | multipart/form-data | 上传 Excel/CSV |

### 教师分页查询示例

```text
GET /teachers?page=1&page_size=20&name=李老师&gender=男&sort_by=hire_date&sort_order=desc
```

### 新增教师请求体示例

```json
{
  "name": "李老师",
  "gender": "男",
  "birth_date": "1990-01-01T00:00:00",
  "phone": "13800138000",
  "email": "li@example.com",
  "title": "班主任",
  "class_id": 1,
  "hire_date": "2024-09-01T00:00:00"
}
```

---

## 3.8 统计模块 `/statistics`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 查询年龄大于 X 的学生 | GET | `/statistics/ge_stu/plus` | Query | `skip` `limit` `age` |
| 学生总人数 | GET | `/statistics/stu_count` | 无 | 返回总人数 |
| 查询每次考试都高于 X 分的学生 | GET | `/statistics/score_greater/plus` | Query | `skip` `limit` `grade` |
| 查询 2 次以上不及格学生 | GET | `/statistics/score_fails` | Query | `skip` `limit` |
| 查询各班平均分 | GET | `/statistics/class_avg` | Query | `skip` `limit` |
| 查询薪资最高前 N 人 | GET | `/statistics/tall_sal` | Query | `limit` |
| 查询学生就业时长 | GET | `/statistics/job_time` | Query | `skip` `limit` |
| 查询班级平均就业时长 | GET | `/statistics/avg_class_job_time` | Query | `skip` `limit` |

### 统计查询示例

```text
GET /statistics/tall_sal?limit=10
```

---

## 3.9 AI 作业模块 `/work`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 生成学生评价 | POST | `/work/evaluation` | Query | `student_id` `style` |
| 文生图 | POST | `/work/image` | Query | `prompt` |
| 获取会话列表 | GET | `/work/talks/sessions` | 无 | 返回当前登录用户会话 |
| 创建新会话 | POST | `/work/talks/sessions` | JSON Body | 需传 `user_id` `title`，但后端以当前登录用户为准 |
| 删除会话 | DELETE | `/work/talks/sessions/{session_id}` | Path | 逻辑删除 |
| 获取会话消息 | GET | `/work/talks/{session_id}/messages` | Path | 历史消息 |
| 多轮对话 | POST | `/work/talks` | JSON Body | 需传 `session_id` `user_id` `prompt`，但后端以当前登录用户为准 |
| 清空会话消息 | POST | `/work/talks/clear` | Query | `session_id` |
| 天气查询 | GET | `/work/weather` | Query | `location` 或 `adcode` 二选一 |
| 地址解析 | GET | `/work/geocoder` | Query | `address` `policy` |

### 学生评价调用示例

```text
POST /work/evaluation?student_id=1&style=幽默
```

### 文生图调用示例

```text
POST /work/image?prompt=一只在草地上奔跑的柯基犬
```

### 创建会话请求体示例

```json
{
  "user_id": "当前登录用户名",
  "title": "Dify 新会话"
}
```

> 说明：`user_id` 虽然在 schema 中必传，但后端实际会使用当前 Bearer Token 对应的登录用户。

### 多轮对话请求体示例

```json
{
  "session_id": 1,
  "user_id": "当前登录用户名",
  "prompt": "请根据我的学生数据给出学习建议"
}
```

### 清空会话示例

```text
POST /work/talks/clear?session_id=1
```

### 天气查询示例

```text
GET /work/weather?adcode=110000&weather_type=now
```

### 地址解析示例

```text
GET /work/geocoder?address=北京市海淀区中关村&policy=0
```

---

## 3.10 邮件模块 `/email`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 生成邮件内容 | POST | `/email/generate` | Query | `prompt` |
| 发送邮件 | POST | `/email/send` | Query | `subject` `body` `receiver` |

### 生成邮件调用示例

```text
POST /email/generate?prompt=给张老师写一封请假两天的邮件
```

### 发送邮件调用示例

```text
POST /email/send?subject=请假申请&body=老师您好，我因身体不适请假两天。&receiver=teacher@example.com
```

---

## 3.11 NL2SQL 模块 `/nl2sql`

| 功能 | 方法 | URL | 参数位置 | 说明 |
|------|------|-----|----------|------|
| 智能问数 | POST | `/nl2sql/query` | JSON Body | 传自然语言问题 |
| 获取表结构概览 | GET | `/nl2sql/schema` | 无 | 返回可查询表和 schema 文本 |
| 获取历史会话 | GET | `/nl2sql/sessions` | 无 | 返回当前登录用户历史记录 |

### NL2SQL 查询请求体示例

```json
{
  "question": "就业薪资最高的前5名学生是谁？",
  "session_id": null
}
```

> 说明：schema 中虽然有 `user_id` 字段，但后端实际使用当前登录用户，不依赖外部传入值。

---

## 4. 适合 Dify 直接配置成工具的接口建议

### 4.1 智能问数工具

- 方法：`POST`
- URL：`/nl2sql/query`
- Header：`Authorization: Bearer {{token}}`
- Body：

```json
{
  "question": "{{question}}",
  "session_id": {{session_id}}
}
```

推荐输入变量：

- `question`：用户自然语言问题
- `session_id`：可选，支持多轮追问

---

### 4.2 学生评价工具

- 方法：`POST`
- URL：`/work/evaluation?student_id={{student_id}}&style={{style}}`
- Header：`Authorization: Bearer {{token}}`

推荐输入变量：

- `student_id`
- `style`：`幽默 / 严肃 / 激励 / 批判`

---

### 4.3 天气工具

- 方法：`GET`
- URL：`/work/weather?adcode={{adcode}}&weather_type={{weather_type}}`
- Header：`Authorization: Bearer {{token}}`

推荐输入变量：

- `adcode`
- `weather_type`：`now / future / hours`

---

### 4.4 地址解析工具

- 方法：`GET`
- URL：`/work/geocoder?address={{address}}&policy={{policy}}`
- Header：`Authorization: Bearer {{token}}`

---

### 4.5 邮件生成工具

- 方法：`POST`
- URL：`/email/generate?prompt={{prompt}}`
- Header：`Authorization: Bearer {{token}}`

---

### 4.6 邮件发送工具

- 方法：`POST`
- URL：`/email/send?subject={{subject}}&body={{body}}&receiver={{receiver}}`
- Header：`Authorization: Bearer {{token}}`

---

## 5. Dify 接入时的实际建议

### 建议 1：单独创建 Dify 服务账号

建议在本系统里创建一个专门给 Dify 用的账号，例如：

- 用户名：`dify_bot`
- 角色：只给 Dify 需要的权限

这样做比直接用 admin 更安全。

---

### 建议 2：不要把所有接口都暴露给 Dify

优先开放：

- 查询类接口
- NL2SQL
- 统计类接口
- AI 能力接口
- 邮件生成接口

谨慎开放：

- 删除类接口
- 系统用户/角色管理接口
- 物理删除接口

---

### 建议 3：注意本项目里有“POST + Query 参数”接口

这类接口在 Dify 里最容易配错。以下接口不要把参数放 JSON body：

- `/work/evaluation`
- `/work/image`
- `/work/talks/clear`
- `/email/generate`
- `/email/send`
- `/score/is_delete`

这些都应该放在 URL Query 参数中。

---

### 建议 4：文件上传接口通常不适合作为聊天工具第一批接入

这两个接口需要 `multipart/form-data`：

- `/score/import`
- `/teachers/import`

建议先把查询、NL2SQL、AI 能力接通，再考虑文件上传工作流。

---

## 6. 最小可用接入方案

如果你想先把 Dify 跑通，最小方案建议只接：

1. `POST /auth/login`
2. `POST /nl2sql/query`
3. `GET /nl2sql/schema`
4. `GET /statistics/stu_count`
5. `POST /work/evaluation`
6. `GET /work/weather`
7. `POST /email/generate`

这样就能先实现：

- 登录鉴权
- 智能问数
- 基础统计
- AI 学生评价
- 天气查询
- 邮件草稿生成

---

## 7. 补充说明

1. 本项目默认所有业务接口都受 RBAC 保护，没 token 会返回 `401`，没权限会返回 `403`。  
2. `NL2SQL`、`多轮对话`、`系统管理` 都已经和当前登录用户绑定，不建议靠外部传 `user_id` 控制身份。  
3. 就业模块路径前缀是 `/Employment`，注意大小写。  
4. 教师模块接口没有统一前缀，路径是 `/teacher`、`/teachers/...`。  
5. 如果后续要做更稳的 Dify 集成，建议再单独封装一层“面向 Agent 的聚合接口”，而不是让 Dify 直接操作全部底层 CRUD。
