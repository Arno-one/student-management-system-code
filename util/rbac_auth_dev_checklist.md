# RBAC 登录系统开发实施清单

> 更新时间：2026-06-06
> 范围：FastAPI 后端 + Vue 前端 `frontend-vue/` + 用户/角色管理页（仅 admin 默认可见）

---

## 1. 数据库与权限目录

- [x] 设计 RBAC 表结构：`sys_user / sys_role / sys_permission / sys_user_role / sys_role_permission`
- [x] 编写初始化 SQL：`util/rbac_auth_init.sql`
- [x] 初始化默认 `admin` 角色与 `admin` 账号
- [x] 初始化页面权限、接口权限、系统管理权限目录
- [x] 用户已执行 SQL

---

## 2. 后端基础认证能力

- [x] 新增认证配置项：`AUTH_SECRET_KEY / AUTH_TOKEN_EXPIRE_MINUTES / AUTH_PBKDF2_ITERATIONS`
- [x] 新增密码哈希与 JWT 工具：`util/auth.py`
- [x] 新增 RBAC 鉴权依赖：`util/rbac.py`
- [x] 新增 RBAC ORM 模型：`model/Auth.py`
- [x] 新增 RBAC DAO：`DAO/auth_dao.py`
- [x] 新增认证业务层：`service/auth_service.py`
- [x] 新增认证接口：`API/auth_api.py`
- [x] 新增系统管理接口：`API/system_api.py`
- [x] 补充 `database.py` 启动时加载 RBAC 模型
- [x] 补充 `requirements.txt` 中的 JWT 依赖

---

## 3. 后端路由接入鉴权

- [ ] `main.py` 注册 `/auth` 与 `/system` 路由
- [ ] 学生模块接入权限校验
- [ ] 成绩模块接入权限校验
- [ ] 就业模块接入权限校验
- [ ] 班级模块接入权限校验
- [ ] 教师模块接入权限校验
- [ ] 统计模块接入权限校验
- [ ] AI 作业模块接入权限校验
- [ ] 邮件模块接入权限校验
- [ ] NL2SQL 模块接入权限校验
- [ ] 多轮对话 / NL2SQL 会话标识切换为“使用当前登录用户”

---

## 4. Vue 登录态与路由权限

- [ ] 改造 `frontend-vue/src/api/index.js`：支持 Bearer Token、登录态持久化、文件下载/上传鉴权
- [ ] 新增登录页 `LoginView.vue`
- [ ] 新增 `/login` 路由
- [ ] 新增 `/system` 路由
- [ ] 增加路由守卫：未登录跳登录页、无页面权限禁止进入
- [ ] `App.vue` 支持登录页空白布局
- [ ] `Sidebar.vue` 按菜单权限动态显示导航
- [ ] `TopBar.vue` 展示当前登录用户并支持退出登录

---

## 5. 用户 / 角色管理页

- [ ] 新增系统管理页 `SystemView.vue`
- [ ] 用户列表查询
- [ ] 新增用户
- [ ] 更新用户
- [ ] 重置用户密码
- [ ] 分配用户角色
- [ ] 角色列表查询
- [ ] 新增角色
- [ ] 更新角色
- [ ] 为角色分配权限
- [ ] 仅拥有 `system:page` 且角色为 `admin` 的账号可见并可访问

---

## 6. 前端业务页权限细化

- [ ] 菜单级权限控制已覆盖所有页面
- [ ] 关键操作按钮按权限显隐（create / update / delete / import 等）
- [ ] 工作台多轮对话不再要求手输 user_id
- [ ] NL2SQL 自动使用当前登录用户身份

---

## 7. 联调与验收

- [ ] `admin / Admin@123456` 可以成功登录
- [ ] 未登录访问业务接口返回 401
- [ ] 无权限访问业务接口返回 403
- [ ] 非 admin 账号无法访问用户/角色管理页
- [ ] 修改角色后刷新登录态可看到权限变化
- [ ] 禁用账号后无法继续登录
- [ ] 首次登录需改密标记能正确返回

---

## 当前进度说明

当前已完成：
1. 数据库与初始化脚本
2. 后端认证/RBAC 的核心基础代码
3. 开发实施清单文档落盘

当前正在进行：
1. 将认证系统注册到 `main.py`
2. 给现有业务接口挂权限
3. 改造 Vue 登录态与系统管理页
