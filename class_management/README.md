# 班级管理

## 班级表 (classes)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK | 主键 |
| name | VARCHAR(50) | NOT NULL | 班级名称 |
| created_time | DATETIME | DEFAULT NOW | 创建时间 |
| updated_time | DATETIME | ON UPDATE NOW | 更新时间 |
| deleted_at | DATETIME | - | 逻辑删除 |
