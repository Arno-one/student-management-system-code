-- ============================================
-- 登录认证 + RBAC 权限系统 — 建表与初始化脚本
-- 适用数据库：MySQL 5.7+ / 8.0
-- 执行方式：切换到业务库后，整段执行本脚本
--
-- 默认超级管理员：admin
-- 默认密码：Admin@123456
-- 注意：首次登录后请尽快修改默认密码
--
-- 设计约定：
-- 1) 用户/角色管理页统一作为“系统管理页”处理，权限码：system:page
-- 2) 首版仅初始化一个超级管理员角色：admin（角色名：超级管理员）
-- 3) system:page 及全部 system:* 管理权限默认只授予 admin 角色
-- 4) 业务权限统一采用“模块:动作”格式，如：student:view / student:create
-- ============================================

SET NAMES utf8mb4;

-- ============================================
-- 1. 用户表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_user` (
    `id`                   INT           NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username`             VARCHAR(50)   NOT NULL                COMMENT '登录账号',
    `password_hash`        VARCHAR(255)  NOT NULL                COMMENT '密码哈希（PBKDF2-SHA256）',
    `real_name`            VARCHAR(50)   NOT NULL                COMMENT '真实姓名',
    `phone`                VARCHAR(20)   DEFAULT NULL            COMMENT '手机号',
    `email`                VARCHAR(100)  DEFAULT NULL            COMMENT '邮箱',
    `status`               TINYINT       NOT NULL DEFAULT 1      COMMENT '状态 1-启用 0-禁用',
    `must_change_password` TINYINT       NOT NULL DEFAULT 0      COMMENT '首次登录是否必须修改密码 1-是 0-否',
    `last_login_at`        DATETIME      DEFAULT NULL            COMMENT '最后登录时间',
    `pwd_updated_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最近修改密码时间',
    `is_deleted`           TINYINT       NOT NULL DEFAULT 0      COMMENT '逻辑删除 0-未删 1-已删',
    `create_time`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_sys_user_username` (`username`),
    KEY `idx_sys_user_status` (`status`),
    KEY `idx_sys_user_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';


-- ============================================
-- 2. 角色表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_role` (
    `id`          INT           NOT NULL AUTO_INCREMENT COMMENT '角色ID',
    `role_code`   VARCHAR(50)   NOT NULL                COMMENT '角色编码，如 admin',
    `role_name`   VARCHAR(50)   NOT NULL                COMMENT '角色名称',
    `status`      TINYINT       NOT NULL DEFAULT 1      COMMENT '状态 1-启用 0-禁用',
    `is_deleted`  TINYINT       NOT NULL DEFAULT 0      COMMENT '逻辑删除 0-未删 1-已删',
    `remark`      VARCHAR(255)  DEFAULT NULL            COMMENT '备注',
    `create_time` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_sys_role_code` (`role_code`),
    KEY `idx_sys_role_status` (`status`),
    KEY `idx_sys_role_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统角色表';


-- ============================================
-- 3. 权限表
--    permission_type：
--      - menu   ：菜单/页面权限
--      - action ：操作权限（前端按钮 + 后端接口共用）
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_permission` (
    `id`              INT           NOT NULL AUTO_INCREMENT COMMENT '权限ID',
    `permission_code` VARCHAR(100)  NOT NULL                COMMENT '权限编码，如 student:view',
    `permission_name` VARCHAR(100)  NOT NULL                COMMENT '权限名称',
    `permission_type` VARCHAR(20)   NOT NULL                COMMENT '权限类型 menu/action',
    `module`          VARCHAR(50)   NOT NULL                COMMENT '所属模块，如 student/score/system',
    `action`          VARCHAR(50)   DEFAULT NULL            COMMENT '动作，如 page/view/create/update/delete',
    `route_path`      VARCHAR(100)  DEFAULT NULL            COMMENT '前端路由，仅 menu 类型有值',
    `visible`         TINYINT       NOT NULL DEFAULT 1      COMMENT '菜单是否展示 1-展示 0-不展示',
    `sort_no`         INT           NOT NULL DEFAULT 0      COMMENT '排序号',
    `status`          TINYINT       NOT NULL DEFAULT 1      COMMENT '状态 1-启用 0-禁用',
    `description`     VARCHAR(255)  DEFAULT NULL            COMMENT '权限说明',
    `create_time`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_sys_permission_code` (`permission_code`),
    KEY `idx_sys_permission_module` (`module`),
    KEY `idx_sys_permission_type` (`permission_type`),
    KEY `idx_sys_permission_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统权限表';


-- ============================================
-- 4. 用户-角色关联表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_user_role` (
    `user_id`      INT       NOT NULL COMMENT '用户ID',
    `role_id`      INT       NOT NULL COMMENT '角色ID',
    `create_time`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`user_id`, `role_id`),
    KEY `idx_sys_user_role_role_id` (`role_id`),
    CONSTRAINT `fk_sys_user_role_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_sys_user_role_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户-角色关联表';


-- ============================================
-- 5. 角色-权限关联表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_role_permission` (
    `role_id`      INT       NOT NULL COMMENT '角色ID',
    `permission_id` INT      NOT NULL COMMENT '权限ID',
    `create_time`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`role_id`, `permission_id`),
    KEY `idx_sys_role_permission_permission_id` (`permission_id`),
    CONSTRAINT `fk_sys_role_permission_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_sys_role_permission_permission` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统角色-权限关联表';


-- ============================================
-- 6. 初始化权限目录
--    说明：
--    - menu 类型：控制页面/左侧导航是否展示
--    - action 类型：控制按钮显隐 + 后端接口访问
--    - system:page 为“用户/角色管理页”的入口权限，默认只有 admin 拥有
-- ============================================
INSERT INTO `sys_permission`
(`permission_code`, `permission_name`, `permission_type`, `module`, `action`, `route_path`, `visible`, `sort_no`, `status`, `description`)
VALUES
-- 学生管理
('student:page', '学生信息页', 'menu', 'student', 'page', '/student', 1, 10, 1, '进入学生信息管理页面'),
('student:view', '查看学生', 'action', 'student', 'view', NULL, 0, 11, 1, '查看学生列表与详情'),
('student:create', '新增学生', 'action', 'student', 'create', NULL, 0, 12, 1, '创建学生'),
('student:update', '编辑学生', 'action', 'student', 'update', NULL, 0, 13, 1, '更新学生信息'),
('student:delete', '删除学生', 'action', 'student', 'delete', NULL, 0, 14, 1, '逻辑删除学生'),
('student:restore', '恢复学生', 'action', 'student', 'restore', NULL, 0, 15, 1, '恢复已删除学生'),

-- 成绩管理
('score:page', '成绩管理页', 'menu', 'score', 'page', '/score', 1, 20, 1, '进入成绩管理页面'),
('score:view', '查看成绩', 'action', 'score', 'view', NULL, 0, 21, 1, '查看成绩列表与详情'),
('score:create', '新增成绩', 'action', 'score', 'create', NULL, 0, 22, 1, '新增成绩记录'),
('score:update', '编辑成绩', 'action', 'score', 'update', NULL, 0, 23, 1, '更新成绩记录'),
('score:delete', '删除成绩', 'action', 'score', 'delete', NULL, 0, 24, 1, '删除成绩记录'),
('score:import', '导入成绩', 'action', 'score', 'import', NULL, 0, 25, 1, '批量导入成绩'),

-- 就业管理
('employment:page', '就业信息页', 'menu', 'employment', 'page', '/employment', 1, 30, 1, '进入就业信息管理页面'),
('employment:view', '查看就业信息', 'action', 'employment', 'view', NULL, 0, 31, 1, '查看就业信息'),
('employment:create', '新增就业信息', 'action', 'employment', 'create', NULL, 0, 32, 1, '创建就业信息'),
('employment:update', '编辑就业信息', 'action', 'employment', 'update', NULL, 0, 33, 1, '更新就业信息'),
('employment:delete', '删除就业信息', 'action', 'employment', 'delete', NULL, 0, 34, 1, '删除就业信息'),

-- 班级管理
('class:page', '班级管理页', 'menu', 'class', 'page', '/class', 1, 40, 1, '进入班级管理页面'),
('class:view', '查看班级', 'action', 'class', 'view', NULL, 0, 41, 1, '查看班级列表与详情'),
('class:create', '新增班级', 'action', 'class', 'create', NULL, 0, 42, 1, '创建班级'),
('class:update', '编辑班级', 'action', 'class', 'update', NULL, 0, 43, 1, '更新班级信息'),
('class:delete', '删除班级', 'action', 'class', 'delete', NULL, 0, 44, 1, '删除班级信息'),

-- 教师管理
('teacher:page', '教师管理页', 'menu', 'teacher', 'page', '/teacher', 1, 50, 1, '进入教师管理页面'),
('teacher:view', '查看教师', 'action', 'teacher', 'view', NULL, 0, 51, 1, '查看教师列表与详情'),
('teacher:create', '新增教师', 'action', 'teacher', 'create', NULL, 0, 52, 1, '创建教师'),
('teacher:update', '编辑教师', 'action', 'teacher', 'update', NULL, 0, 53, 1, '更新教师信息'),
('teacher:delete', '删除教师', 'action', 'teacher', 'delete', NULL, 0, 54, 1, '删除教师信息'),
('teacher:import', '导入教师', 'action', 'teacher', 'import', NULL, 0, 55, 1, '批量导入教师数据'),

-- 统计分析
('statistics:page', '统计分析页', 'menu', 'statistics', 'page', '/statistics', 1, 60, 1, '进入统计分析页面'),
('statistics:view', '查看统计分析', 'action', 'statistics', 'view', NULL, 0, 61, 1, '查看统计分析结果'),

-- AI 作业
('work:page', 'AI作业页', 'menu', 'work', 'page', '/work', 1, 70, 1, '进入 AI 作业页面'),
('work:use', '使用AI作业模块', 'action', 'work', 'use', NULL, 0, 71, 1, '使用 AI 作业相关能力'),

-- 邮件管理
('email:page', '邮件管理页', 'menu', 'email', 'page', '/email', 1, 80, 1, '进入邮件管理页面'),
('email:send', '发送邮件', 'action', 'email', 'send', NULL, 0, 81, 1, '生成并发送邮件'),

-- NL2SQL
('nl2sql:page', 'NL2SQL页', 'menu', 'nl2sql', 'page', '/nl2sql', 1, 90, 1, '进入 NL2SQL 页面'),
('nl2sql:use', '使用NL2SQL', 'action', 'nl2sql', 'use', NULL, 0, 91, 1, '发起自然语言问数'),

-- 系统管理：用户 / 角色管理页（仅 admin 默认拥有）
('system:page', '系统管理页', 'menu', 'system', 'page', '/system', 1, 100, 1, '进入用户/角色管理页，仅超级管理员默认拥有'),
('system:user:view', '查看用户', 'action', 'system', 'user:view', NULL, 0, 101, 1, '查看系统用户列表与详情'),
('system:user:create', '新增用户', 'action', 'system', 'user:create', NULL, 0, 102, 1, '创建系统用户'),
('system:user:update', '编辑用户', 'action', 'system', 'user:update', NULL, 0, 103, 1, '更新系统用户信息'),
('system:user:reset-password', '重置用户密码', 'action', 'system', 'user:reset-password', NULL, 0, 104, 1, '重置用户密码'),
('system:user:assign-roles', '分配用户角色', 'action', 'system', 'user:assign-roles', NULL, 0, 105, 1, '为用户分配角色'),
('system:role:view', '查看角色', 'action', 'system', 'role:view', NULL, 0, 106, 1, '查看角色列表与详情'),
('system:role:create', '新增角色', 'action', 'system', 'role:create', NULL, 0, 107, 1, '创建角色'),
('system:role:update', '编辑角色', 'action', 'system', 'role:update', NULL, 0, 108, 1, '更新角色信息'),
('system:role:assign-permissions', '分配角色权限', 'action', 'system', 'role:assign-permissions', NULL, 0, 109, 1, '为角色分配权限')
ON DUPLICATE KEY UPDATE
    `permission_name` = VALUES(`permission_name`),
    `permission_type` = VALUES(`permission_type`),
    `module` = VALUES(`module`),
    `action` = VALUES(`action`),
    `route_path` = VALUES(`route_path`),
    `visible` = VALUES(`visible`),
    `sort_no` = VALUES(`sort_no`),
    `status` = VALUES(`status`),
    `description` = VALUES(`description`),
    `update_time` = CURRENT_TIMESTAMP;


-- ============================================
-- 7. 初始化角色
--    仅初始化一个超级管理员角色：admin
-- ============================================
INSERT INTO `sys_role`
(`role_code`, `role_name`, `status`, `is_deleted`, `remark`)
VALUES
('admin', '超级管理员', 1, 0, '拥有系统全部权限，默认唯一可访问用户/角色管理页')
ON DUPLICATE KEY UPDATE
    `role_name` = VALUES(`role_name`),
    `status` = VALUES(`status`),
    `is_deleted` = VALUES(`is_deleted`),
    `remark` = VALUES(`remark`),
    `update_time` = CURRENT_TIMESTAMP;


-- ============================================
-- 8. 初始化默认超级管理员账号
--    账号：admin
--    密码：Admin@123456
--    哈希算法：PBKDF2-SHA256（迭代 600000 次）
--
--    说明：这里使用 INSERT IGNORE，避免重复执行脚本时把你后续修改过的密码重置掉
-- ============================================
INSERT IGNORE INTO `sys_user`
(`username`, `password_hash`, `real_name`, `phone`, `email`, `status`, `must_change_password`, `is_deleted`)
VALUES
('admin', 'pbkdf2_sha256$600000$EcirAzviim9tIMvcTfGUVg$dKlFNgdN3HsTid8gt52ne6iIb6W-HnJvXd7Xy62e-uU', '系统超级管理员', NULL, NULL, 1, 1, 0);


-- ============================================
-- 9. 绑定 admin 用户 -> admin 角色
-- ============================================
INSERT IGNORE INTO `sys_user_role` (`user_id`, `role_id`)
SELECT u.`id`, r.`id`
FROM `sys_user` u
JOIN `sys_role` r ON r.`role_code` = 'admin'
WHERE u.`username` = 'admin';


-- ============================================
-- 10. 为 admin 角色授予全部权限
--     这样首版登录后可完整访问现有系统与系统管理页
-- ============================================
INSERT IGNORE INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT r.`id`, p.`id`
FROM `sys_role` r
JOIN `sys_permission` p
WHERE r.`role_code` = 'admin';
