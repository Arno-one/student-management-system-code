"""
教师管理业务逻辑层 — MVC中的Model业务逻辑部分
"""
from sqlalchemy.orm import Session
from typing import List, Literal, Optional
from datetime import datetime
from io import BytesIO
import csv
import io
import math

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from pydantic import ValidationError

from DAO.teacher_information_CRUD import teacher_table_CRUD
from model import Teacher
from scheme.teacher_scheme import POST_Teacher_Info, PUT_Teacher_Info, GET_Teacher_Info
from util.log import get_logger

# 本模块专用 logger，来源标记为 service.teacher_service
logger = get_logger(__name__)

# ============ 教师 Excel/CSV 导入相关常量 ============
# Excel/CSV 表头（中文）→ 教师字段名 的映射。
# 用中文表头让 HR/教务在 Excel 里填表时一目了然，比直接写英文字段直观得多。
IMPORT_COLUMN_MAP = {
    "姓名": "name",
    "性别": "gender",
    "出生日期": "birth_date",
    "联系电话": "phone",
    "邮箱": "email",
    "职务": "title",
    "所带班级ID": "class_id",
    "入职日期": "hire_date",
}
# 模板里表头出现的先后顺序（也是导出/下载模板时的列顺序）
IMPORT_HEADERS = list(IMPORT_COLUMN_MAP.keys())
# 必填列：缺一不可，少了直接判定该行失败
IMPORT_REQUIRED_FIELDS = ["name", "gender", "phone", "title", "class_id", "hire_date"]
# 字段名 → 中文，用于把校验错误信息翻译成人话返回给前端
FIELD_CN = {
    "name": "姓名", "gender": "性别", "birth_date": "出生日期", "phone": "联系电话",
    "email": "邮箱", "title": "职务", "class_id": "所带班级ID", "hire_date": "入职日期",
}


def get_teacher_by_id(id: int, db: Session) -> GET_Teacher_Info:
    """根据ID查询教师"""
    crud = teacher_table_CRUD(db)
    teacher = crud.read(id)
    if teacher is None:
        logger.warning("查询教师失败：教师ID %s 不存在", id)
        raise ValueError(f"教师ID {id} 不存在")
    return GET_Teacher_Info.model_validate(teacher)


def search_teachers(
    db: Session,
    name: str = None,
    gender: str = None,
    title: str = None,
    class_id: int = None,
    phone: str = None,
    email: str = None,
    hire_date_start: datetime = None,
    hire_date_end: datetime = None,
    sort_by: str = None,
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
):
    """分页搜索教师"""
    GENDER_TO_ENUM = {"男": Teacher.gender.man, "女": Teacher.gender.woman}
    crud = teacher_table_CRUD(db)

    filters = {
        "name": name,
        "title": title,
        "class_id": class_id,
        "phone": phone,
        "email": email,
        "hire_date_start": hire_date_start,
        "hire_date_end": hire_date_end,
    }
    if gender:
        filters["gender"] = GENDER_TO_ENUM.get(gender)

    items, total = crud.search(
        filters=filters, sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size,
    )

    return {
        "items": [GET_Teacher_Info.model_validate(t) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


def create_teachers(teacher_list: List[POST_Teacher_Info], db: Session):
    """批量创建教师"""
    # 批量写入是关键节点，记录本批次条数
    logger.info("批量创建教师开始：本批次 %s 条", len(teacher_list))
    crud = teacher_table_CRUD(db)
    new_teacher_orms = [Teacher.Teacher(**t.model_dump()) for t in teacher_list]
    crud.create(new_teacher_orms)
    logger.info("批量创建教师完成：本批次 %s 条", len(teacher_list))


def update_teacher(id: int, data: PUT_Teacher_Info, db: Session):
    """更新教师信息"""
    crud = teacher_table_CRUD(db)
    update_dict = data.model_dump(exclude_none=True)
    crud.update(id, update_dict)
    logger.info("更新教师完成：id=%s, 字段=%s", id, list(update_dict.keys()))


def delete_teacher(id: int, db: Session):
    """删除教师（逻辑删除）"""
    crud = teacher_table_CRUD(db)
    crud.delete(id)
    logger.info("逻辑删除教师完成：id=%s", id)


def create_single_teacher(data: POST_Teacher_Info, db: Session):
    """
    新增单个教师。
    最常见、最直观的操作：前端一个表单填一位老师，提交即可，不用再手写 JSON 数组。
    """
    crud = teacher_table_CRUD(db)
    new_teacher = Teacher.Teacher(**data.model_dump())
    crud.create([new_teacher])
    logger.info("单个新增教师完成：name=%s", data.name)


# ====================== 以下为「Excel/CSV 批量导入」相关实现 ======================

def _clean_text(v):
    """
    把单元格的原始值清洗成"干净的字符串或 None"。
    处理三类常见情况：
      1) Excel 把电话/班级号当数字读进来（int/float），转成不带小数点的字符串；
      2) 字符串两端有空格，统一 strip；
      3) 空字符串 / 空白 一律当成 None，方便后续按"是否为空"判断必填。
    """
    if v is None:
        return None
    if isinstance(v, float):
        # NaN（空单元格在某些解析下会变成 NaN）
        if math.isnan(v):
            return None
        # 13800000000.0 这种整数浮点，去掉小数点
        if v.is_integer():
            return str(int(v))
        return str(v)
    if isinstance(v, int):
        return str(v)
    s = str(v).strip()
    return s or None


def _read_rows(content: bytes, filename: str):
    """
    根据文件名后缀，把上传的 Excel(.xlsx/.xls) 或 CSV 解析成统一的二维结构：
    返回 (表头list, 数据行list[list])。这样后续处理不用关心文件到底是哪种格式。
    """
    name = (filename or "").lower()
    if name.endswith(".csv"):
        # utf-8-sig 能自动吃掉 Excel 导出 CSV 时带的 BOM 头，避免第一列表头读歪
        text = content.decode("utf-8-sig", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = [list(r) for r in reader]
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        # data_only=True：取单元格"计算后的值"而不是公式本身
        wb = load_workbook(BytesIO(content), data_only=True)
        ws = wb.active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        raise ValueError("仅支持 .xlsx / .xls / .csv 格式的文件")

    if not rows:
        raise ValueError("文件内容为空，请使用模板填写后再上传")

    header = [_clean_text(h) for h in rows[0]]
    data_rows = rows[1:]
    return header, data_rows


def import_teachers_from_file(content: bytes, filename: str, db: Session) -> dict:
    """
    从上传的 Excel/CSV 批量导入教师。
    业务友好策略：逐行校验，合格的直接入库，不合格的不影响其它行，
    最后返回一份"成功多少条、失败多少条、每个失败行的具体原因"的汇总，
    让使用者一眼就知道哪一行哪里填错了。
    """
    header, data_rows = _read_rows(content, filename)

    # 1) 先确认表头里必须的列都在，缺列就没法继续了
    header_set = set(h for h in header if h)
    missing_cols = [col for col in IMPORT_HEADERS
                    if IMPORT_COLUMN_MAP[col] in IMPORT_REQUIRED_FIELDS and col not in header_set]
    if missing_cols:
        raise ValueError(f"模板表头缺少必填列：{'、'.join(missing_cols)}，请下载标准模板填写")

    # 表头中文 → 它在每行里的列下标，方便按字段取值
    col_index = {IMPORT_COLUMN_MAP[h]: idx for idx, h in enumerate(header) if h in IMPORT_COLUMN_MAP}

    valid_infos: List[POST_Teacher_Info] = []
    failures: list[dict] = []
    effective_total = 0  # 真正参与处理的行数（跳过全空行）

    for offset, row in enumerate(data_rows):
        excel_row_no = offset + 2  # +2：表头占第1行，数据从第2行开始，对应 Excel 里的真实行号

        # 整行都是空的就跳过（Excel 末尾经常带一堆空行）
        if row is None or all(_clean_text(c) is None for c in row):
            continue
        effective_total += 1

        # 按字段名把这一行的值取出来并清洗
        def cell(field):
            idx = col_index.get(field)
            if idx is None or idx >= len(row):
                return None
            return _clean_text(row[idx])

        name = cell("name")
        gender = cell("gender")
        phone = cell("phone")
        try:
            # 班级ID 单独转成整数；填了非数字给出清晰的中文提示
            class_id_raw = cell("class_id")
            if class_id_raw is None:
                class_id = None
            else:
                try:
                    class_id = int(float(class_id_raw))
                except (ValueError, TypeError):
                    raise ValueError(f"所带班级ID 必须是数字（当前填的是「{class_id_raw}」）")

            # 性别只认"男/女"，其它值提前拦下，给出清晰提示
            if gender is not None and gender not in ("男", "女"):
                raise ValueError("性别只能填 男 或 女")

            payload = {
                "name": name,
                "gender": gender,
                "birth_date": cell("birth_date"),
                "phone": phone,
                "email": cell("email"),
                "title": cell("title"),
                "class_id": class_id,
                "hire_date": cell("hire_date"),
            }
            # 交给 Pydantic 做类型/必填/邮箱格式等完整校验
            info = POST_Teacher_Info(**payload)
            valid_infos.append(info)
        except ValidationError as ve:
            # 把 Pydantic 的英文错误翻译成"哪个字段 + 什么问题"
            reasons = []
            for err in ve.errors():
                loc = err.get("loc") or []
                field = loc[0] if loc else ""
                reasons.append(f"{FIELD_CN.get(field, field)}：{err.get('msg')}")
            failures.append({"row": excel_row_no, "name": name, "reason": "；".join(reasons)})
        except (ValueError, TypeError) as e:
            failures.append({"row": excel_row_no, "name": name, "reason": str(e)})

    # 2) 把所有合格的教师一次性入库（DAO 内部是一个事务，整体提交）
    if valid_infos:
        crud = teacher_table_CRUD(db)
        crud.create([Teacher.Teacher(**info.model_dump()) for info in valid_infos])

    result = {
        "total": effective_total,
        "success_count": len(valid_infos),
        "fail_count": len(failures),
        "failures": failures,
    }
    logger.info("教师导入完成：共 %s 行，成功 %s 条，失败 %s 条",
                effective_total, len(valid_infos), len(failures))
    return result


def build_import_template() -> BytesIO:
    """
    生成"教师批量导入"的标准 Excel 模板（带表头、示例行、简单样式）。
    使用者下载后照着填、再上传即可，避免自己瞎猜该填哪些列、什么格式。
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "教师导入模板"

    # 表头行
    ws.append(IMPORT_HEADERS)
    # 一行示例数据，给使用者做参考
    ws.append(["李老师", "男", "1990-05-20", "13800000000", "li@example.com", "讲师", 1, "2024-09-01"])

    # ===== 简单美化：表头加粗 + 蓝底白字 + 居中，并设置合适的列宽 =====
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="2563EB")
    center = Alignment(horizontal="center", vertical="center")
    for col_idx, _ in enumerate(IMPORT_HEADERS, start=1):
        c = ws.cell(row=1, column=col_idx)
        c.font = header_font
        c.fill = header_fill
        c.alignment = center
        ws.column_dimensions[c.column_letter].width = 16

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio
