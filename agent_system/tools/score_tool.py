"""成绩查询工具 — 封装 service/score_service.query_scores()"""
from sqlalchemy.orm import Session
from langchain_core.tools import tool

from agent_system.tools.base import BaseTool, ToolContext
from service import score_service
from util.log import get_logger

logger = get_logger(__name__)


class ScoreTool(BaseTool):
    name = "score_tool"
    description = "查询学生的考试成绩，按学号、考试序次等条件筛选"
    inputs_schema = {"student_no": str, "exam_order": int}

    def run(self, ctx: ToolContext) -> dict:
        student_no = ctx.params.get("student_no", "")
        exam_order = ctx.params.get("exam_order")
        return _query_student_score(db=ctx.db, student_no=student_no, exam_order=exam_order)


@tool
def query_student_score(
    student_no: str,
    exam_order: int | None = None,
) -> dict:
    """
    查询学生考试成绩。返回该学生的成绩列表。

    Args:
        student_no: 学号
        exam_order: 考试序次（可选），不传则返回所有考试记录
    """
    # 实际调用由 executor 完成，此处定义工具签名。
    pass


def _query_student_score(
    db: Session,
    student_no: str,
    exam_order: int | None = None,
) -> dict:
    """内部实现"""
    try:
        result, page, page_size, total = score_service.query_scores(
            db=db,
            student_no=student_no,
            exam_order=exam_order,
            page=1,
            page_size=20,
            sort_no="asc",
        )

        scores = []
        for s in result:
            scores.append({
                "student_no": s.student_no,
                "student_name": s.student.student_name if s.student else "",
                "exam_order": s.exam_order,
                "score": float(s.score) if s.score else 0,
            })

        logger.info("成绩查询成功: student_no=%s, count=%s", student_no, len(scores))
        return {
            "success": True,
            "student_no": student_no,
            "scores": scores,
            "total": total,
            "error": None,
        }
    except ValueError as e:
        logger.warning("成绩查询失败（无数据）: student_no=%s, %s", student_no, e)
        return {
            "success": False,
            "student_no": student_no,
            "scores": [],
            "total": 0,
            "error": str(e),
        }
    except Exception as e:
        logger.exception("成绩查询异常: student_no=%s, %s", student_no, e)
        return {
            "success": False,
            "student_no": student_no,
            "scores": [],
            "total": 0,
            "error": f"成绩查询失败: {e}",
        }
