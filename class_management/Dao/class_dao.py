from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from model.Class import Class,ClassCreateSchema


#新增修改数据
def create_or_update_class(db: Session, class_data: ClassCreateSchema, id=None):
    # 如果是更新操作，直接获取并修改对象，而不是先删后增
    if id is not None:
        class_to_update = db.query(Class).filter(Class.id == id).first()
        if not class_to_update:
            print(f" 修改失败：ID为 {id} 的班级不存在")
            return None
        # 将新数据覆盖到现有对象上
        for key, value in class_data.model_dump().items():
            setattr(class_to_update, key, value)
        db_obj = class_to_update
    else:
        # 新增操作
        db_obj = Class(**class_data.model_dump())
        db.add(db_obj)

    try:
        db.commit()
        db.refresh(db_obj)
        action = "修改" if id is not None else "新增"
        print(f"{action}班级成功：{db_obj}")
        return db_obj
    except SQLAlchemyError as e:
        db.rollback()
        action = "修改" if id is not None else "新增"
        print(f"{action}班级失败: {e}")
        return None



#删除数据
def del_class(db:Session,id):
    try:
        class_to_del:Class = db.query(Class).filter(Class.id == id,Class.is_deleted == 0)
        class_to_del.is_deleted = 1
        db.commit()
        db.refresh()
    except Exception as e:
        print(e)

#根据id查询数据
def get_class(db:Session,id) -> Optional[Class]:
    class_by_id:Class = db.query(Class).filter(Class.id == id,Class.is_deleted == 0).first()

    print("根据id查询:",class_by_id.class_name if class_by_id else "没有该班级")
    return class_by_id
