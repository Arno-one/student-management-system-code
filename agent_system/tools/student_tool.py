"""学生身份解析工具 — C2 逻辑：默认 username→学号 映射，可传参覆盖"""
from sqlalchemy.orm import Session
from langchain_core.tools import tool

from agent_system.tools.base import BaseTool, ToolContext
from DAO import student_dao
from util.log import get_logger

logger = get_logger(__name__)


class StudentTool(BaseTool):
    name = "student_tool"
    description = "根据当前登录用户解析目标学生信息，默认 username 作为学号查询"
    inputs_schema = {"current_username": str, "student_no_override": str}

    def run(self, ctx: ToolContext) -> dict:
        current_username = ctx.params.get("current_username", ctx.user.get("username", ""))
        student_no_override = ctx.params.get("student_no_override")
        return _resolve_student(db=ctx.db, current_username=current_username, student_no_override=student_no_override)


@tool
def resolve_student(
    current_username: str,
    student_no_override: str | None = None,
) -> dict:
    """
    根据当前登录用户解析目标学生信息。
    默认将 username 作为学号查询 Student 表；管理员可传 student_no_override 覆盖。

    Returns:
        {"found": bool, "student_no": str, "student_name": str, "class_id": int, "error": str|None}
    """
    # 注意：此函数需要 db session，但在 LangChain @tool 中无法直接注入 FastAPI Depends。
    # 实际运行时由 executor 在调用前手动注入 db；此处定义工具签名供 Planner 引用。
    # executor 中会这样调用：
    #   result = resolve_student.invoke({
    #       "current_username": user["username"],
    #       "student_no_override": student_no,
    #   })
    # 但 resolve_student 真正需要 db，所以 executor 会绕过 @tool 直接调内部函数。
    pass


def _resolve_student(
    db: Session,
    current_username: str,
    student_no_override: str | None = None,
) -> dict:
    """
    内部实现：根据 username 推导 student_no，可传参覆盖。

    逻辑：
    1. 如果传了 student_no_override → 直接用它查 Student 表
    2. 否则用 current_username 作为学号查 Student 表
    3. 查到 → 返回学生信息
    4. 查不到 → 返回 found=False + 提示
    """
    target_no = student_no_override or current_username

    student = student_dao.get_by_student_no(target_no, db)
    if student:
        logger.info("学生身份解析成功: username=%s → student_no=%s, name=%s",
                    current_username, student.student_no, student.student_name)
        return {
            "found": True,
            "student_no": student.student_no,
            "student_name": student.student_name,
            "class_id": student.class_id,
            "error": None,
        }

    # 用原始 username 查不到时的提示
    if student_no_override:
        hint = f"未找到学号为 {student_no_override} 的学生"
    else:
        hint = f"未找到与账号 {current_username} 关联的学生信息，请传入学号参数"

    logger.warning("学生身份解析失败: username=%s, override=%s, hint=%s",
                   current_username, student_no_override, hint)
    return {
        "found": False,
        "student_no": target_no,
        "student_name": "",
        "class_id": 0,
        "error": hint,
    }
