"""
成绩管理Controller层 — MVC中的Controller
只负责HTTP请求/响应处理，不包含业务逻辑
"""
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from database import get_db
from scheme.schema_score import Addscore, Updatescore, ScoreExtract
from scheme.response_scheme import success, success_page
from service import score_service, extract_service
from decimal import Decimal
from typing import List, Optional, Literal
from util.log import get_logger
from util.rbac import require_permission

# 本模块专用 logger，来源标记为 API.score_api
logger = get_logger(__name__)

router_score = APIRouter()


class NLExtractRequest(BaseModel):
    """自然语言提取请求"""
    text: str = Field(..., description="自然语言描述", min_length=1, max_length=2000)


_SCORE_REQUIRED_FIELDS = ["student_no", "exam_order", "score"]


@router_score.post("/extract", summary="自然语言提取成绩信息", dependencies=[Depends(require_permission('score:create'))])
def extract_score(body: NLExtractRequest):
    logger.info("NL提取成绩：text=%s", body.text[:80])
    result = extract_service.extract_fields(
        text=body.text,
        schema=ScoreExtract,
        entity="score",
        required_fields=_SCORE_REQUIRED_FIELDS,
    )
    if result["error"]:
        logger.warning("NL提取成绩失败：%s", result["error"])
    else:
        logger.info("NL提取成绩成功：提取字段=%s, 缺失=%s",
                    list(result["extracted"].keys()) if result["extracted"] else 0,
                    result["missing_required"])
    return success(result)


@router_score.post("/add", summary="新增单个学生成绩", dependencies=[Depends(require_permission('score:create'))])
def add_score_api(new_score: Addscore, db=Depends(get_db)):
    logger.info("新增成绩：student_no=%s, exam_order=%s, score=%s",
                new_score.student_no, new_score.exam_order, new_score.score)
    try:
        result = score_service.add_score(new_score, db)
        logger.info("新增成绩成功：student_no=%s, exam_order=%s",
                    result.student_no, result.exam_order)
        return success({
            "student_no": result.student_no,
            "student_name": result.student.student_name,
            "exam_order": result.exam_order,
            "score": result.score,
        }, "学生成绩信息添加成功")
    except ValueError as e:
        logger.warning("新增成绩失败：student_no=%s, %s", new_score.student_no, e)
        raise HTTPException(status_code=400 if "已存在" in str(e) else 404,
                            detail=str(e))


@router_score.get("/import/template", summary="下载成绩导入模板", dependencies=[Depends(require_permission('score:import'))])
def download_score_import_template():
    logger.info("下载成绩导入模板")
    bio = score_service.build_import_template()
    headers = {"Content-Disposition": "attachment; filename=score_import_template.xlsx"}
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router_score.post("/import", summary="上传 Excel/CSV 批量导入成绩", dependencies=[Depends(require_permission('score:import'))])
async def import_scores_api(
    file: UploadFile = File(...),
    db=Depends(get_db)
):
    logger.info("批量导入成绩：文件名=%s", file.filename)
    try:
        content = await file.read()
        result = score_service.import_scores_from_file(content, file.filename, db)
        msg = f"导入完成：成功 {result['success_count']} 条，失败 {result['fail_count']} 条"
        logger.info("批量导入成绩成功：%s", msg)
        return success(result, msg)
    except ValueError as e:
        logger.warning("批量导入成绩参数错误：%s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("批量导入成绩异常：%s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router_score.post("/batch_add", summary="批量添加学生成绩", dependencies=[Depends(require_permission('score:create'))])
def batch_add_score_api(
    score_list: List[Addscore],
    db=Depends(get_db)
):
    logger.info("批量新增成绩：共 %s 条", len(score_list))
    try:
        result = score_service.batch_add_scores(score_list, db)
        logger.info("批量新增成绩成功：实际添加 %s 条", len(result))
        return success(
            [{"student_no": i.student_no,
              "student_name": i.student.student_name,
              "exam_order": i.exam_order,
              "score": Decimal(i.score)} for i in result],
            f"批量添加成功！共添加 {len(result)} 条成绩"
        )
    except ValueError as e:
        logger.warning("批量新增成绩失败：%s", e)
        raise HTTPException(status_code=400 if "已存在" in str(e) else 404,
                            detail=str(e))


@router_score.put("/update", summary="修改学生成绩", dependencies=[Depends(require_permission('score:update'))])
def update_score_api(new_score: Updatescore, db=Depends(get_db)):
    logger.info("修改成绩：student_no=%s, exam_order=%s",
                new_score.student_no, new_score.exam_order)
    try:
        result = score_service.update_score(new_score, db)
        logger.info("修改成绩成功：student_no=%s, exam_order=%s",
                    result.student_no, result.exam_order)
        return success({
            "student_no": result.student_no,
            "student_name": result.student.student_name,
            "exam_order": result.exam_order,
            "score": result.score,
        }, "学生成绩信息修改成功")
    except ValueError as e:
        logger.warning("修改成绩失败：student_no=%s, %s", new_score.student_no, e)
        raise HTTPException(status_code=404, detail=str(e))


@router_score.post("/is_delete", summary="删除学生成绩", dependencies=[Depends(require_permission('score:delete'))])
def is_delete_api(
    student_no: str = Query(...,
                            min_length=8, max_length=10,
                            pattern=r"^S\d+$",
                            description="学生编号必填（如：S2025001）"),
    exam_order: int = Query(..., ge=1, description="考试次序"),
    db=Depends(get_db)
):
    logger.info("删除成绩：student_no=%s, exam_order=%s", student_no, exam_order)
    try:
        result = score_service.soft_delete_score(student_no, exam_order, db)
        logger.info("删除成绩成功：student_no=%s, exam_order=%s", student_no, exam_order)
        return success({
            "student_no": result.student_no,
            "student_name": result.student.student_name,
            "exam_order": result.exam_order,
            "score": result.score,
        }, "学生成绩删除成功")
    except ValueError as e:
        logger.warning("删除成绩失败：student_no=%s, %s", student_no, e)
        raise HTTPException(status_code=404, detail=str(e))


@router_score.get("/query", summary="查询学生的成绩", dependencies=[Depends(require_permission('score:view'))])
def query_score_api(
    db=Depends(get_db),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，1~100"),
    student_no: str = Query(None, min_length=8, max_length=10,
                            pattern=r"^S\d+$",
                            description="学生编号（如：S2025001）"),
    exam_order: Optional[int] = Query(None, ge=1, description="考试序次"),
    class_id: Optional[int] = Query(None, ge=1, description="班级id"),
    min_score: Optional[Decimal] = Query(None, ge=0, le=100,
                                         description="查询的最低范围成绩"),
    max_score: Optional[Decimal] = Query(None, ge=0, le=100,
                                         description="查询的最高范围成绩"),
    sort_no: Literal["asc", "desc"] = Query(None,
                                            description="按学号排序asc升序,desc降序,不填就不排"),
    sort_score: Literal["asc", "desc"] = Query(None,
                                               description="asc升序,desc降序,不填就不排")
):
    logger.info("查询成绩：student_no=%s, exam_order=%s, class_id=%s, page=%s, page_size=%s",
                student_no, exam_order, class_id, page, page_size)
    try:
        result, page_num, size, total = score_service.query_scores(
            db, page, page_size,
            student_no, exam_order, class_id,
            min_score, max_score,
            sort_no, sort_score
        )
        return success_page(
            [{"student_no": i.student_no,
              "student_name": i.student.student_name,
              "class_id": i.student.class_id,
              "exam_order": i.exam_order,
              "score": i.score} for i in result],
            page_num, size, total, "学生信息查询成功"
        )
    except ValueError as e:
        logger.warning("查询成绩失败：%s", e)
        raise HTTPException(status_code=400 if "范围" in str(e) else 404,
                            detail=str(e))
