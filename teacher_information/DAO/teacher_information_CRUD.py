from model import Teacher
from datetime import datetime

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

    def read(self,id=-1):
        if id==-1:
            return self.db.query(Teacher.Teacher).filter(Teacher.Teacher.is_deleted==0).all()
        else:
            return self.db.query(Teacher.Teacher).filter(Teacher.Teacher.id==id , Teacher.Teacher.is_deleted==0).first()
        
    def update(self,id,update_data:dict):
        temp_Teacher=self.db.query(Teacher.Teacher).filter(Teacher.Teacher.id==id, Teacher.Teacher.is_deleted==0).first()
        if temp_Teacher:
            for key,value in update_data.items():
                if hasattr(temp_Teacher,key):
                    setattr(temp_Teacher,key,value)
            setattr(temp_Teacher,'update_time',datetime.now())
            self.db.commit()
            self.db.refresh(temp_Teacher)
            return temp_Teacher
        else:
            raise Exception("id错误")
        
    def delete(self,id):
        temp_Teacher=self.db.query(Teacher.Teacher).filter(Teacher.Teacher.id==id, Teacher.Teacher.is_deleted==0).first()
        if temp_Teacher:
            setattr(temp_Teacher,'update_time',datetime.now())
            setattr(temp_Teacher,'is_deleted',1)
            self.db.commit()
        else:
            raise Exception("id错误")


        


