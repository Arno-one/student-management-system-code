from model.Class import Class
from datetime import datetime

#新增修改数据
def create_or_update_class(db, class_data, id=None):
    # 如果是更新操作，直接获取并修改对象，而不是先删后增
    if id is not None:
        class_to_update = db.query(Class).filter(Class.id == id).first()
        if not class_to_update:
            print(f" 修改失败：ID为 {id} 的班级不存在")
            return None
        # 将新数据覆盖到现有对象上
        for key, value in class_data.model_dump().items():
            setattr(class_to_update, key, value)
        db_obj : Class = class_to_update
        #更新修改时间
        db_obj.update_time = datetime.now()

    else:
        # 新增操作
        #判断编号是否重复
        if get_class_by_code(db,class_data.class_code):
            db_obj = Class(**class_data.model_dump())
            db.add(db_obj)

    try:
        db.commit()
        db.refresh(db_obj)
        action = "修改" if id is not None else "新增"
        print(f"{action}班级成功：{db_obj}")
        return db_obj
    except Exception as e:
        db.rollback()
        action = "修改" if id is not None else "新增"
        print(f"{action}班级失败: {e}")
        return None

#删除数据
def del_class(db,id):
    try:
        class_to_del:Class = db.query(Class).filter(Class.id == id,Class.is_deleted == 0).first()
        class_to_del.is_deleted = 1
        db.commit()
        db.refresh(class_to_del)
        return f"删除{class_to_del.class_name}成功"
    except Exception as e:
        print(e)
        return f"没有id为{id}的数据删除"

#查询所有班级数据
def get_class(db,page,limit):
    all_user = db.query(Class).filter(Class.is_deleted == 0).offset(page*limit).limit(limit).all()
    return all_user

#根据id查询数据
def get_class_by_id(db,id):
    class_by_id:Class = db.query(Class).filter(Class.id == id,Class.is_deleted == 0).first()
    print("根据id查询:",class_by_id.class_name if class_by_id else "没有该班级")
    return class_by_id if class_by_id else "没有该班级"

#根据班级编号查询数据
def get_class_by_code(db,code):
    class_by_code:Class = db.query(Class).filter(Class.class_code == code,Class.is_deleted == 0).first()
    print("根据id查询:",class_by_code.class_name if class_by_code else "没有该班级")
    return False if class_by_code else True