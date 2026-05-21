from fastapi import APIRouter,Depends
from database import get_db
from model.Class import ClassCreateSchema
from class_management.Dao import class_dao

class_router = APIRouter()

@class_router.post("/create_or_update_class")
def create_or_update_class(class_data:ClassCreateSchema,id:int=None,db = Depends(get_db)):
    class_dao.create_or_update_class(db = db, class_data=class_data, id=id)
    return class_data

@class_router.delete("/del_class")
def del_class(id:int,db = Depends(get_db) ):
    class_dao.del_class(db = db,id = id)

@class_router.get("/get_class/{id}")
def get_class(id:int,db = Depends(get_db)):
    return class_dao.get_class(db = db,id = id)

