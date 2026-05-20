# 学生就业管理

## 就业信息表 (employment)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK | 主键 |
| created_time | DATETIME | DEFAULT NOW | 创建时间 |
| updated_time | DATETIME | ON UPDATE NOW | 更新时间 |
| deleted_at | DATETIME | - | 逻辑删除 |
