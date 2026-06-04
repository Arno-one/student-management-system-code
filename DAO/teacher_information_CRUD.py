from model import Teacher
from datetime import datetime
from sqlalchemy.orm import joinedload
from util.log import get_logger

# 本模块专用 logger，来源标记为 DAO.teacher_information_CRUD
logger = get_logger(__name__)

class teacher_table_CRUD:
    def __init__(self,db):
        self.db=db

    def create(self,Teacher_list:list[Teacher.Teacher]):
        for i in Teacher_list:
            i.update_time=datetime.now()
        self.db.add_all(Teacher_list)
        self.db.commit()
        for i in Teacher_list:
            self.db.refresh(i)
        logger.info("教师批量入库（事务已提交）：共 %s 条", len(Teacher_list))

    def read(self,id=-1):
        query = (
            self.db.query(Teacher.Teacher)
            .options(joinedload(Teacher.Teacher.classname))
            .filter(Teacher.Teacher.is_deleted == 0)
        )
        if id == -1:
            return query.all()
        else:
            return query.filter(Teacher.Teacher.id == id).first()
        
    def update(self,id,update_data:dict):
        temp_Teacher=self.db.query(Teacher.Teacher).filter(Teacher.Teacher.id==id, Teacher.Teacher.is_deleted==0).first()
        if temp_Teacher:
            for key,value in update_data.items():
                if hasattr(temp_Teacher,key):
                    setattr(temp_Teacher,key,value)
               
            setattr(temp_Teacher,'update_time',datetime.now())
            self.db.commit()
            self.db.refresh(temp_Teacher)
            logger.info("教师信息已更新（事务已提交）：id=%s", id)
            return temp_Teacher
        else:
            logger.warning("更新教师失败：id=%s 不存在", id)
            raise Exception("id错误")
        
    def search(self, filters: dict = None, sort_by: str = None, sort_order: str = "asc", page: int = 1, page_size: int = 20):
        base = self.db.query(Teacher.Teacher).filter(Teacher.Teacher.is_deleted == 0)

        if filters:
            if filters.get("name"):
                base = base.filter(Teacher.Teacher.name.like(f"%{filters['name']}%"))
            if filters.get("gender") is not None:
                base = base.filter(Teacher.Teacher.gender == filters["gender"])
            if filters.get("title"):
                base = base.filter(Teacher.Teacher.title == filters["title"])
            if filters.get("class_id") is not None:
                base = base.filter(Teacher.Teacher.class_id == filters["class_id"])
            if filters.get("phone"):
                base = base.filter(Teacher.Teacher.phone.like(f"%{filters['phone']}%"))
            if filters.get("email"):
                base = base.filter(Teacher.Teacher.email.like(f"%{filters['email']}%"))
            if filters.get("hire_date_start"):
                base = base.filter(Teacher.Teacher.hire_date >= filters["hire_date_start"])
            if filters.get("hire_date_end"):
                base = base.filter(Teacher.Teacher.hire_date <= filters["hire_date_end"])

        total = base.count()

        query = base.options(joinedload(Teacher.Teacher.classname))

        SORT_COLUMNS = {
            "id": Teacher.Teacher.id,
            "name": Teacher.Teacher.name,
            "hire_date": Teacher.Teacher.hire_date,
            "create_time": Teacher.Teacher.create_time,
            "class_id": Teacher.Teacher.class_id,
        }
        if sort_by and sort_by in SORT_COLUMNS:
            col = SORT_COLUMNS[sort_by]
            query = query.order_by(col.desc() if sort_order == "desc" else col.asc())

        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def delete(self,id):
        temp_Teacher=self.db.query(Teacher.Teacher).filter(Teacher.Teacher.id==id, Teacher.Teacher.is_deleted==0).first()
        if temp_Teacher:
            setattr(temp_Teacher,'update_time',datetime.now())
            setattr(temp_Teacher,'is_deleted',1)
            self.db.commit()
            logger.info("教师已逻辑删除（事务已提交）：id=%s", id)
        else:
            logger.warning("删除教师失败：id=%s 不存在", id)
            raise Exception("id错误")


        


