from pydantic import BaseModel
from datetime import datetime

class ClassCreateSchema(BaseModel):
    class_code: str
    class_name: str
    start_time: datetime
    head_teacher_id: int

class ClassInfo(BaseModel):
    id : int
    class_code: str
    class_name: str
    start_time: datetime
    is_deleted: int
    create_time: datetime
    update_time: datetime