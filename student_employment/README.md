# 学生就业管理

## 就业信息表 (employment)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | AUTO_INCREMENT | 就业ID |
| student_no      | VARCHAR(50)  | NOT NULL       | 学生编号      |
| student_name    | VARCHAR(50)  | NOT NULL       | 学生姓名      |
| class_id        | INT          | NOT NULL       | 班级ID        |
| job_open_time | DATE | DEFAULT NULL | 就业开放时间 |
| offer_send_time | DATE | DEFAULT NULL | offer下发时间 |
| company_name | VARCHAR(100) | DEFAULT NULL | 就业公司 |
| salary | INT | DEFAULT NULL | 就业薪资 |
| deleted_at | TINYINT | DEFAULT 0 | 逻辑删除 |
| created_time | DATETIME | DEFAULT NOW | 创建时间 |
| updated_time | DATETIME | ON UPDATE NOW | 更新时间 |
