from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List
#添加成绩校验
class Addscore(BaseModel):
    student_no : str = Field(...,min_length=8,
                             max_length=10,
                             pattern="^S\d+$",
                             description="学生编号必填（如：S2025001）")
    exam_order : int = Field(...,ge=1,description="考试次序")
    score : Decimal = Field(...,ge=0,le=100,description="考试成绩")

#批量添加模型（包装列表）
class BatchAddScore(BaseModel):
    score_list: List[Addscore]

#更新成绩校验
class Updatescore(BaseModel):
    student_no: str = Field(...,min_length=8,
                            max_length=10,
                            pattern="^S\d+$",
                            description="学生编号必填（如：S2025001）")
    exam_order: int = Field(..., ge=1, description="考试次序")
    score: Decimal = Field(..., ge=0, le=100, description="考试成绩")


