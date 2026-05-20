# 统计分析

## 统计报表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK | 主键 |
| created_time | DATETIME | DEFAULT NOW | 创建时间 |
| updated_time | DATETIME | ON UPDATE NOW | 更新时间 |
