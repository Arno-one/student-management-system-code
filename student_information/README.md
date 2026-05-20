# 学生基本信息管理

## 学生表 (students)

| 字段名          | 数据类型     | 约束 / 属性                                           | 说明                       |
| --------------- | ------------ | ----------------------------------------------------- | -------------------------- |
| id              | INT          | PRIMARY KEY, INDEX, AUTO_INCREMENT                    | 主键，学生 id              |
| student_no      | VARCHAR(50)  | UNIQUE, NOT NULL, INDEX                               | 学生学号                   |
| class_id        | INT          | NOT NULL, INDEX                                       | 班级 ID                    |
| student_name    | VARCHAR(50)  | NOT NULL, INDEX                                       | 学生姓名                   |
| gender          | VARCHAR(10)  | NOT NULL                                              | 性别                       |
| age             | INT          | NOT NULL                                              | 年龄                       |
| native_place    | VARCHAR(100) | -                                                     | 籍贯                       |
| graduate_school | VARCHAR(100) | -                                                     | 毕业院校                   |
| major           | VARCHAR(100) | -                                                     | 专业                       |
| education       | VARCHAR(50)  | -                                                     | 学历                       |
| admission_time  | DATE         | -                                                     | 入学时间                   |
| graduate_time   | DATE         | -                                                     | 毕业时间                   |
| advisor_id      | INT          | -                                                     | 顾问编号                   |
| is_deleted      | INT          | NOT NULL, DEFAULT '0'                                 | 逻辑删除 0 - 未删 1 - 已删 |
| create_time     | DATETIME     | DEFAULT CURRENT_TIMESTAMP                             | 创建时间                   |
| update_time     | DATETIME     | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间                   |

