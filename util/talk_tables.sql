-- ============================================
-- 多轮记忆对话 — 建表语句
-- 数据库：student_management
-- ============================================

-- 会话表：按 user_id 隔离用户，一个用户可有多个会话
CREATE TABLE IF NOT EXISTS `talk_session` (
    `id`            INT           NOT NULL AUTO_INCREMENT  COMMENT '会话ID',
    `user_id`       VARCHAR(100)  NOT NULL                 COMMENT '用户标识（对话隔离）',
    `session_title` VARCHAR(200)  NOT NULL DEFAULT '新对话' COMMENT '会话标题',
    `summary`       TEXT          DEFAULT NULL             COMMENT '对话主题摘要（大模型自动生成）',
    `style`         VARCHAR(100)  DEFAULT NULL             COMMENT '用户对话风格偏好（大模型自动识别）',
    `is_deleted`    TINYINT       NOT NULL DEFAULT 0       COMMENT '逻辑删除 0-未删 1-已删',
    `create_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';


-- 消息表：user_content 存用户问题，ai_content 存大模型回复
CREATE TABLE IF NOT EXISTS `talk_message` (
    `id`           INT           NOT NULL AUTO_INCREMENT  COMMENT '消息ID',
    `session_id`   INT           NOT NULL                 COMMENT '所属会话ID',
    `role`         VARCHAR(20)   NOT NULL                 COMMENT '角色: system / user / assistant',
    `user_content` TEXT          DEFAULT NULL             COMMENT '用户问题（role=user 时有值）',
    `ai_content`   TEXT          DEFAULT NULL             COMMENT '大模型回复（role=assistant 时有值）',
    `create_time`  DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_session_id` (`session_id`),
    CONSTRAINT `fk_talk_message_session` FOREIGN KEY (`session_id`) REFERENCES `talk_session` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话消息表';
