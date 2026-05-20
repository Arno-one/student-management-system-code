# 学生管理系统

## 教师表 (teachers)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK | 主键 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| gender | ENUM | - | 性别 |
| birth_date | DATE | - | 出生日期 |
| phone | VARCHAR(20) | - | 联系电话 |
| email | VARCHAR(100) | - | 邮箱 |
| title | VARCHAR(50) | - | 职称 |
| class_id | INT | FK, UNIQUE | 所带班级 |
| hire_date | DATE | - | 入职日期 |
| created_time | DATETIME | DEFAULT NOW | 创建时间 |
| updated_time | DATETIME | ON UPDATE NOW | 更新时间 |
| deleted_at | ENUM | - | 逻辑删除 |
