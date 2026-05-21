from fastapi import APIRouter,Depends,Query,HTTPException
from database import get_db
from DAO import score_dao
from decimal import Decimal
from scheme.schema_score import Addscore,Updatescore
from model.Score import Score
from typing import Optional,Literal,List
from DAO.student_dao import get_by_student_no

router_score = APIRouter()

#添加单个学生成绩
@router_score.post("/add",summary="新增学生成绩")
def add_score_api(new_score:Addscore,db=Depends(get_db)):
    exist = get_by_student_no(new_score.student_no,db)
    #先判断在学生表中是否存在该学生
    if not exist:
        raise HTTPException(
            status_code=404,
            detail=f"学生{new_score.student_no}的信息不在学生表中,请检查要添加的学生信息"
        )
    is_exist = score_dao.is_exist(db,new_score.student_no,new_score.exam_order)
    if is_exist:
        raise HTTPException(
            status_code=400,
            detail=f"学生{new_score.student_no}的第{new_score.exam_order}次成绩已经存在,请勿重复添加"
        )
    new = Score(student_no=new_score.student_no, exam_order=new_score.exam_order, score=new_score.score)
    result = score_dao.add_score(db,new)

    return {"message": "学生成绩信息添加成功",
            "添加的数据为": {"student_no": result.student_no,
                             "student_name": result.student.student_name,
                             "exam_order": result.exam_order,
                             "score": result.score}}

#批量添加
@router_score.post("/batch_add", summary="批量添加学生成绩")
def batch_add_score_api(
    score_list: List[Addscore],
    db= Depends(get_db)):
    not_exist = []
    for i in score_list:
        exist = get_by_student_no(i.student_no, db)
        if not exist:
            not_exist.append(i.student_no)
    if not_exist :
        raise HTTPException(
            status_code=404,
            detail=f"学生{not_exist}的信息不在学生表中,请检查要添加的学生信息"
        )
    #存储待插入的对象列表
    batch_data = []
    # 判断传入的列表中是否有已经存在的数据
    for item in score_list:
        # 调用dao的方法判断是否重复
        is_exist = score_dao.is_exist(db=db,
            student_no=item.student_no,
            exam_order=item.exam_order)
        # 如果存在则直接抛出异常
        if is_exist:
            raise HTTPException(
                status_code=400,
                detail=f"学生成绩已存在：学生{item.student_no}第{item.exam_order}次成绩已存在，批量添加终止")

        # 不重复则将数据存入列表
        batch_data.append(Score(
            student_no=item.student_no,
            exam_order=item.exam_order,
            score=item.score)
        )

    # 调用dao中的批量插入方法
    result = score_dao.batch_add_scores(db,batch_data)

    # 返回插入的结果
    return {"message": f"批量添加成功！共添加 {len(batch_data)} 条成绩",
        "data": [{"student_no": i.student_no,
                  "student_name": i.student.student_name,
                  "exam_order": i.exam_order,
                  "score": Decimal(i.score)} for i in batch_data]}


#更新学生信息
@router_score.put("/update",summary="修改学生成绩")
def update_score_api(new_score:Updatescore,db=Depends(get_db)):
    is_exist = score_dao.is_exist(db,new_score.student_no,new_score.exam_order)
    if not is_exist:
        raise HTTPException(
            status_code=404,
            detail="你要修改的学生信息不存在"
        )
    new = score_dao.update_score(db,new_score.student_no,new_score.exam_order,new_score.score)
    return {"message": "学生成绩信息修改成功",
        "修改后的数据为": {
            "student_no": new.student_no,
            "student_name": new.student.student_name,
            "exam_order": new.exam_order,
            "score": new.score
        }}

# 删除单个学生信息
@router_score.post("/is_delete",summary="删除学生成绩")
def is_delete_api( student_no: str = Query(...,min_length=8,max_length=10,pattern="^S\d+$",description="学生编号必填（如：S2025001）"),
                   exam_order: int = Query(...,ge=1,description="考试次序"),
                   db=Depends(get_db)):
    is_exist = score_dao.is_exist(db,student_no,exam_order)
    if not is_exist:
        #不存在就抛出异常
        raise HTTPException(status_code=404,detail="要删除的学生信息不存在")
     #学生信息存在,进行逻辑删除
    new = score_dao.is_delete(db,student_no,exam_order)
    return {"message": "学生成绩删除成功",
        "删除的数据为": {
            "student_no": new.student_no,
            "student_name": new.student.student_name,
            "exam_order": new.exam_order,
            "score": new.score
        }}


#查询学生成绩接口
@router_score.get("/query",summary="查询学生的成绩")
def query_score_api(db=Depends(get_db),
                    page: int = Query(1,ge=1,description="页码，从1开始"),
                    page_size: int = Query(10,ge=1,le=100,description="每页数量，1~100"),
                    student_no:str = Query(None, min_length=8,max_length=10,pattern="^S\d+$", description="学生编号（如：S2025001）"),
                    exam_order: Optional[int]= Query(None,ge=1,description="考试序次"),
                    class_id : Optional[int] = Query(None,ge=1,description="班级id"),
                    min_score: Optional[Decimal] = Query(None,ge=0,le=100,description="查询的最低范围成绩"),
                    max_score: Optional[Decimal] = Query(None,ge=0,le=100,description="查询的最高范围成绩"),
                    sort_no : Literal["asc","desc"] = Query(None,description="按学号排序asc升序,desc降序,不填就不排"),
                    sort_score : Literal["asc","desc"] = Query(None,description="asc升序,desc降序,不填就不排")
                    ):
    if min_score is not None and max_score is not None:
        if min_score > max_score:
            raise HTTPException(status_code=400, detail="请求异常,最小范围不能大于最大范围")

    result = score_dao.query_score(db,page,page_size,student_no,exam_order,class_id,min_score,max_score,sort_no,
                                   sort_score)
    if result:
        return {"message": "学生信息查询成功", "查询到的数据数量为":len(result),"查询到的数据为":
            [{
            "student_no": i.student_no,
            "student_name": i.student.student_name,
            "class_id": i.student.class_id,
            "exam_order": i.exam_order,
            "score": i.score
        } for i in result]}
    else:
        # 不存在就抛出异常
        raise HTTPException(status_code=404, detail="要查询的学生信息不存在")





