"""
项目统一日志系统模块。

一句话作用：在 main.py 启动时调用一次 setup_logging() 就能开启全项目日志功能。

这个日志系统都做了啥（对应你的几点需求）：
1. 每天一个日志文件：每天 0 点自动切分，当天的日志写到当天的文件里。
2. 只保留近 7 天：超过 7 天的旧日志文件会被自动删除，不会越堆越多。
3. 按系统信息分类：日志里会带上"级别 + 来源模块 + 行号"，一眼能看出是哪儿打的、什么级别。
4. ERROR 单独存放：专门有一个 error.log，只收 ERROR 及以上的错误，排查问题时直接看它即可。
5. 控制台同步输出：开发阶段在终端也能实时看到日志，方便调试。

日志文件都放在项目根目录下的 logs/ 文件夹里：
    logs/app.log     —— 全量运行日志（INFO 及以上，含 WARNING / ERROR）
    logs/error.log   —— 只记录 ERROR 及以上的错误日志

其它业务模块以后要打日志时，统一这样拿 logger（先别急着加，等你检查完日志系统再说）：
    from util.log import get_logger
    logger = get_logger(__name__)
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
"""

import os
import sys
import time
import json
import logging
from decimal import Decimal
from datetime import date, datetime
from logging.handlers import TimedRotatingFileHandler

try:
    import sqlparse
except Exception:
    sqlparse = None

# 日志级别、保留天数都从统一配置 config（.env）读取，方便不同环境无需改代码即可调整。
from config import LOG_LEVEL, LOG_BACKUP_DAYS

# ==================== 基础配置 ====================

# 日志统一存放目录：项目根目录下的 logs 文件夹。
# 这里用绝对路径推算，保证不管从哪个目录启动项目，日志都落到同一个地方。
# __file__ 是当前 util/log.py，它的上一级是 util，再上一级才是项目根目录。
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 日志文件保留天数：来自 config（默认 7 天），只保留最近这么多天，更早的自动清理。
BACKUP_DAYS = LOG_BACKUP_DAYS

# 日志输出格式：时间 | 级别 | 来源模块:行号 | 具体信息
# 其中 %(name)s 就是 get_logger(__name__) 传进来的模块名，用来区分日志是哪个模块打的；
# 这一行格式就是"按系统信息分类"的体现 —— 级别、来源一目了然。
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 初始化标记：避免 uvicorn 热重载或被重复 import 时，把同样的 handler 加好几遍，
# 否则同一条日志会被重复写入多次。
_initialized = False


def _resolve_level(level) -> int:
    """
    把日志级别统一解析成 logging 模块认识的整数常量。

    既支持直接传整数（如 logging.INFO），也支持传字符串（如 "INFO"、"debug"）。
    .env 里配的是字符串，这里做个兜底转换；万一写了个不认识的级别，就退回到 INFO。

    :param level: 整数级别或级别字符串
    :return: logging 模块的整数级别常量
    """
    if isinstance(level, int):
        return level
    # getLevelName 传入级别名（大写）会返回对应的整数；传入非法名会返回字符串，需要兜底
    resolved = logging.getLevelName(str(level).upper())
    return resolved if isinstance(resolved, int) else logging.INFO


def _build_timed_handler(filename: str, level: int) -> TimedRotatingFileHandler:
    """
    构造一个"按天切分 + 自动清理旧文件"的文件日志处理器。

    :param filename: 日志文件名（如 app.log），最终会落在 logs 目录下
    :param level: 这个处理器只记录 >= 该级别的日志（比如 ERROR 文件就只收 ERROR 及以上）
    :return: 配置好的 TimedRotatingFileHandler 实例
    """
    handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, filename),
        when="midnight",          # 每天 0 点切分一次，做到"每天一个日志文件"
        interval=1,               # 切分间隔为 1 天
        backupCount=BACKUP_DAYS,  # 只保留最近 7 个历史文件，多出来的自动删除
        encoding="utf-8",         # 用 utf-8，保证中文日志不乱码
    )
    # 切分出来的历史文件后缀用日期，形如 app.log.2026-06-04，方便一眼看出是哪天的日志。
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    return handler


def setup_logging(level=None) -> None:
    """
    初始化全局日志系统。整个项目只需在 main.py 启动时调用一次。

    :param level: 全局最低日志级别，支持整数（logging.INFO）或字符串（"INFO"）。
                  不传时默认用 config 里配置的 LOG_LEVEL（来自 .env，默认 INFO）。
    """
    global _initialized
    # 已经初始化过就直接返回，防止重复添加 handler 导致日志重复打印。
    if _initialized:
        return

    # 没显式传级别就用配置文件里的；再统一解析成 logging 认识的整数常量。
    level = _resolve_level(LOG_LEVEL if level is None else level)

    # logs 目录不存在就先创建出来（exist_ok=True 表示已存在也不报错）。
    os.makedirs(LOG_DIR, exist_ok=True)

    # 拿到根 logger，所有模块的日志最终都会汇聚到这里统一处理。
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 先清空可能已存在的 handler（比如被某些库提前配置过），保证日志输出干净、可控。
    root_logger.handlers.clear()

    # 1) 全量运行日志：INFO 及以上（含 WARNING、ERROR）都写进 app.log。
    root_logger.addHandler(_build_timed_handler("app.log", logging.INFO))

    # 2) 错误日志：只把 ERROR 及以上的写进 error.log，专门用于快速排查问题。
    root_logger.addHandler(_build_timed_handler("error.log", logging.ERROR))

    # 3) 控制台输出：开发阶段方便直接在终端实时看到日志。
    # Windows 终端默认是 GBK 编码，直接打中文日志会乱码，这里把标准输出切成 utf-8。
    # reconfigure 是 Python 3.7+ 才有的方法，用 hasattr 做个兼容性判断更稳妥。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)

    _initialized = True
    # 打一条初始化成功的日志，既能验证系统可用，也能在日志里留下启动痕迹。
    root_logger.info("日志系统初始化完成，日志目录：%s", LOG_DIR)


def get_logger(name: str = None) -> logging.Logger:
    """
    获取一个 logger 实例。各业务模块统一用这个方法来打日志。

    :param name: 一般传 __name__，这样日志里就能显示出是哪个模块打的，方便定位。
    :return: logging.Logger 实例
    """
    return logging.getLogger(name)


def _serialize_sql_param(value):
    """把 SQL 参数转成适合写日志的可读文本。"""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _normalize_sql_params(parameters):
    """统一把 SQLAlchemy 参数转成更易读的结构。"""
    if parameters is None:
        return None
    if isinstance(parameters, dict):
        return {k: _serialize_sql_param(v) for k, v in parameters.items()}
    if isinstance(parameters, (list, tuple)):
        if parameters and isinstance(parameters[0], dict):
            return [
                {k: _serialize_sql_param(v) for k, v in item.items()}
                for item in parameters
            ]
        return [_serialize_sql_param(v) for v in parameters]
    return _serialize_sql_param(parameters)


def _format_sql_for_log(statement: str) -> str:
    """把 SQL 语句格式化成适合日志阅读的多行文本。"""
    sql = (statement or "").strip()
    if not sql:
        return "<empty sql>"
    if sqlparse is not None:
        try:
            return sqlparse.format(
                sql,
                reindent=True,
                keyword_case="upper",
                indent_width=2,
                wrap_after=100,
                comma_first=False,
            )
        except Exception:
            pass
    return sql


def _format_sql_log_message(statement: str, parameters, elapsed_ms: float, rowcount: int | None, engine_name: str) -> str:
    """组装统一 SQL 日志内容。"""
    pretty_sql = _format_sql_for_log(statement)
    normalized_params = _normalize_sql_params(parameters)
    params_text = "null"
    if normalized_params is not None:
        try:
            params_text = json.dumps(normalized_params, ensure_ascii=False, default=_serialize_sql_param)
        except Exception:
            params_text = repr(normalized_params)

    rowcount_text = "unknown" if rowcount is None or rowcount == -1 else str(rowcount)
    return (
        f"SQL执行 | engine={engine_name} | 耗时={elapsed_ms:.2f}ms | rowcount={rowcount_text}\n"
        f"SQL:\n{pretty_sql}\n"
        f"PARAMS:\n{params_text}"
    )


def _should_skip_sql_logging(statement: str) -> bool:
    """跳过噪声较大的框架探测 SQL，保留业务执行 SQL。"""
    sql = (statement or "").strip().upper()
    if not sql:
        return True
    skip_prefixes = (
        "PRAGMA ",
        "SHOW VARIABLES",
        "SHOW WARNINGS",
        "SELECT VERSION()",
        "SELECT DATABASE()",
        "SELECT @@",
        "DESCRIBE ",
    )
    return sql.startswith(skip_prefixes)


def register_sqlalchemy_sql_logging(engine, engine_name: str) -> None:
    """给 SQLAlchemy 引擎注册统一 SQL 日志。"""
    if getattr(engine, "_claude_sql_logging_registered", False):
        return

    sql_logger = get_logger("sql")

    from sqlalchemy import event

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        started = conn.info.get("query_start_time") or []
        start = started.pop() if started else time.perf_counter()
        elapsed_ms = (time.perf_counter() - start) * 1000
        if _should_skip_sql_logging(statement):
            return
        sql_logger.info(
            _format_sql_log_message(statement, parameters, elapsed_ms, cursor.rowcount, engine_name)
        )

    @event.listens_for(engine, "handle_error")
    def handle_error(exception_context):
        conn = exception_context.connection
        started = conn.info.get("query_start_time") if conn is not None else None
        start = started.pop() if started else time.perf_counter()
        elapsed_ms = (time.perf_counter() - start) * 1000
        if _should_skip_sql_logging(exception_context.statement):
            return
        sql_logger.error(
            "%s\nERROR: %s",
            _format_sql_log_message(
                exception_context.statement,
                exception_context.parameters,
                elapsed_ms,
                None,
                engine_name,
            ),
            exception_context.original_exception,
        )

    engine._claude_sql_logging_registered = True


def takeover_uvicorn_loggers() -> None:
    """
    接管 uvicorn 自带的日志，让它们也统一写进我们的 app.log / error.log。

    原理：uvicorn 默认给自己的几个 logger 配了独立 handler，并关掉了向上冒泡（propagate=False），
    所以它的日志不会进我们的文件。这里把它的 handler 清掉、打开 propagate，
    日志就会向上冒泡到根 logger，被我们配置好的文件 handler 统一接住。

    注意：
        - uvicorn / uvicorn.error：负责启动信息、运行错误，转交给我们记录。
        - uvicorn.access：访问日志。因为我们已经有自己的请求日志中间件了，
          再让它冒泡会和我们的访问日志重复，所以这里直接把它关掉，避免一条请求记两遍。

    调用时机：要在 uvicorn 启动并配置好自己的日志「之后」再调用（比如放在 lifespan 启动阶段），
    否则会被 uvicorn 随后的初始化覆盖掉。
    """
    # 启动信息和运行错误：转交给根 logger 统一处理
    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()   # 清掉 uvicorn 自己的 handler
        uv_logger.propagate = True   # 打开冒泡，让日志流向根 logger

    # 访问日志：我们有自己的中间件了，关掉 uvicorn 的，避免重复记录
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False


def register_request_logging(app) -> None:
    """
    给 FastAPI 应用挂一个"请求访问日志"中间件，统一记录每个请求的概况。

    好处：不用在每个接口里手写日志，所有请求的「方法 / 路径 / 状态码 / 耗时」都会被自动记录，
    出问题时能快速定位是哪个接口慢、哪个接口报错。

    记录规则：
        - 正常返回：按状态码记日志，>=500 记为 ERROR，>=400 记为 WARNING，其余记为 INFO。
        - 中途抛异常：记一条 ERROR（带耗时），再把异常抛出去交给全局异常处理器统一处理。

    :param app: FastAPI 应用实例
    """
    # 单独用一个名为 access 的 logger，日志里能一眼看出这是访问日志。
    access_logger = get_logger("access")

    @app.middleware("http")
    async def log_requests(request, call_next):
        # perf_counter 是高精度计时器，专门用来算耗时，比 time.time() 更准。
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # 请求处理过程中抛了异常：先记一条带耗时的错误日志，再原样抛出，
            # 交给 main.py 里的全局异常处理器去返回统一结构并记录堆栈。
            cost_ms = (time.perf_counter() - start) * 1000
            access_logger.error(
                "%s %s | 处理异常中断 | 耗时 %.2fms",
                request.method, request.url.path, cost_ms,
            )
            raise

        # 算出本次请求耗时（毫秒）
        cost_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        # 根据状态码选择日志级别：5xx 是服务端错误、4xx 是客户端错误、其余算正常。
        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        access_logger.log(
            level,
            "%s %s | %s | 耗时 %.2fms",
            request.method, request.url.path, status, cost_ms,
        )
        return response
