from fastapi import APIRouter,Depends,HTTPException,Query
from database import get_db
from scheme.class_scheme import ClassCreateSchema as ccs ,ClassInfo
from DAO import class_dao
from scheme.statistical_request import PageResponse

class_router = APIRouter()

@class_router.post("/create_or_update_class",description='新增修改班级数据')
def create_or_update_class(class_data:ccs,id:int=None,db = Depends(get_db)):
    new_class_data = class_dao.create_or_update_class(db = db, class_data=class_data, id=id)
    if not new_class_data:
        raise HTTPException(status_code=404, detail="新增数据班级编号不能重复")
    else:
        return new_class_data

@class_router.delete("/del_class",description='删除班级数据')
def del_class(id:int,db = Depends(get_db) ):
    return class_dao.del_class(db = db, id = id)

@class_router.get(
    "/get_class",
     description='分页查询所有数据'
    ,response_model=PageResponse[ClassInfo])
def get_class(db = Depends(get_db),page:int=Query(default=1,ge=1),limit:int=Query(default=1,ge=1)):
    info = class_dao.get_class(db=db, page=page - 1, limit=limit)
    return PageResponse(data=info,page=page,total=len(info))



@class_router.get("/get_class/{id}",description='根据id')
def get_class(id:int,db = Depends(get_db)):
    return class_dao.get_class_by_id(db = db, id = id)

