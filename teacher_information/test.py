from model import Teacher
from database import Session
from DAO.teacher_information_CRUD import teacher_table_CRUD
from datetime import datetime
import time

if __name__ == "__main__":
    Teacher.Base.metadata.drop_all(Teacher.engine)
    Teacher.Base.metadata.create_all(Teacher.engine)

    db = Session()
    dao = teacher_table_CRUD(db)

    # 测试新增
    t1 = Teacher.Teacher(
        name="张三",
        gender=Teacher.gender.man,
        phone="13800138001",
        email="zhangsan@qq.com",
        title="班主任",
        class_id=1,
        hire_date="2024-09-01 00:00:00",
    )
    t2 = Teacher.Teacher(
        name="李四",
        gender=Teacher.gender.man,
        phone="13800138001",
        email="zhangsan@qq.com",
        title="助教",
        class_id=1,
        hire_date="2024-09-01 00:00:00",
    )
    dao.create([t1,t2])
    print(f"新增后: id={t1.id}, create_time={t1.create_time}, update_time={t1.update_time}")
    time.sleep(1)

    # 查询
    t = dao.read(id=t1.id)
    print(f"查询后: id={t.id}, create_time={t.create_time}, update_time={t.update_time}")

    # 更新前 sleep 一下，方便观察时间变化
    time.sleep(1)

    # 测试更新
    dao.update(t1.id, {"phone": "13900139001", "title": "年级主任"})
    updated = dao.read(id=t1.id)
    print(f"更新后: id={updated.id}, phone={updated.phone}, title={updated.title}, "
          f"create_time={updated.create_time}, update_time={updated.update_time}")

    time.sleep(1)

    # 测试逻辑删除
    dao.delete(t1.id)
    deleted_record = dao.read(id=t1.id)
    print(f"删除后: id={deleted_record.id}, is_deleted={deleted_record.is_deleted}, "
          f"create_time={deleted_record.create_time}, update_time={deleted_record.update_time}")

    db.close()
    print("测试完成")
 