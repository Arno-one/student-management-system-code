from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware  # 跨域中间件，前端页面调用接口需要
from fastapi.exceptions import RequestValidationError  # 参数校验异常
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException  # 兜底所有 HTTP 异常
import uvicorn
from database import init_db
from API.statistical import sta_router
from API.score_api import router_score
from API.class_api import class_router
from API.student_api import student_router
from API.employment_api import employment_router
from API.teacher_information_API_Router import teacher_information_router
from API.work_api import woker, email_router
from API.nl2sql_api import nl2sql_router
from API.auth_api import auth_router
from API.system_api import system_router
from RAG.controller import rag_router
from agent_system.api import agent_router
from agent_system.tools.mcp_client import tencent_map_mcp_client
from util.log import setup_logging, get_logger, register_request_logging, takeover_uvicorn_loggers

# ===== 初始化日志系统 =====
# 注意放在这里（模块顶部）而不是放进 __main__ 代码块：
# 因为 uvicorn 开了 reload=True 后，真正跑应用的是它 fork 出来的子进程，
# __main__ 代码块只在父进程执行一次，子进程并不会跑到那里。
# 放在模块顶部能保证父子进程都完成日志初始化，日志才不会丢。
setup_logging()
# 拿一个本模块专用的 logger，后续记录应用启动 / 关闭等关键节点
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库"""
    # 此时 uvicorn 已经配置好自己的日志了，这里再接管，把它的日志并入我们的文件。
    takeover_uvicorn_loggers()
    logger.info("应用启动中：开始初始化数据库……")
    init_db()
    # MCP 是增强能力，初始化失败也不能影响主应用启动，业务工具会自动回退原有 REST 链路。
    await tencent_map_mcp_client.startup()
    logger.info("数据库初始化完成，应用已就绪")
    try:
        yield
    finally:
        await tencent_map_mcp_client.shutdown()
        logger.info("应用正在关闭")


app = FastAPI(title='学生信息管理系统',
              description='逐光小组作品',
              version='0.5.0',
              lifespan=lifespan)

# ===== 注册请求访问日志中间件 =====
# 放在 CORS 之前注册：这样 CORS 中间件在更外层，能保证错误响应也带上跨域头，
# 同时访问日志中间件能完整覆盖到每一个进来的请求。
register_request_logging(app)

# ===== 配置 CORS 跨域 =====
# 前端 index.html 不管是用文件方式打开还是用本地静态服务器打开，
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 允许的来源，* 表示全部
    allow_credentials=False,  # 注意：来源为 * 时不能同时开启凭证，否则浏览器会拒绝
    allow_methods=["*"],      # 允许所有请求方法（GET/POST/PUT/PATCH/DELETE 等）
    allow_headers=["*"],      # 允许所有请求头
)


# ===== 全局异常处理：让"报错"也返回统一结构 {code, msg, data, total} =====
CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理 HTTPException（如 404、400、409 等业务抛出的异常）"""
    # 这类一般是业务主动抛的预期内异常（如资源不存在），记为 WARNING 即可，方便追溯哪个请求触发的。
    logger.warning(
        "业务异常 %s | %s %s | detail=%s",
        exc.status_code, request.method, request.url.path, exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": str(exc.detail), "data": None, "total": None},
        headers=CORS_HEADERS,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理参数校验失败（FastAPI 默认返回 422，这里把详细错误塞进 data 字段）"""
    # 参数校验失败多是前端传参问题，记为 WARNING，并带上具体是哪些字段错了，方便联调排查。
    logger.warning(
        "参数校验失败 | %s %s | errors=%s",
        request.method, request.url.path, exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "msg": "参数校验失败",
            "data": jsonable_encoder(exc.errors()),  # 具体哪个字段错了
            "total": None,
        },
        headers=CORS_HEADERS,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底处理所有未捕获的异常，避免直接抛出原始堆栈给前端"""
    # 这是最关键的错误记录点：未被捕获的异常说明是程序 bug 或意外情况。
    # 用 logger.exception 会把完整堆栈一并写进 error.log，线上排查问题全靠它。
    logger.exception(
        "服务器内部错误 | %s %s | %s",
        request.method, request.url.path, exc,
    )
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": f"服务器内部错误: {exc}", "data": None, "total": None},
        headers=CORS_HEADERS,
    )


# 学生基本信息管理模块
app.include_router(student_router, prefix='/student', tags=['学生基本信息管理'])
# 登录认证模块
app.include_router(auth_router, prefix='/auth', tags=['登录认证'])
# 系统管理模块（用户 / 角色 / 权限）
app.include_router(system_router, prefix='/system', tags=['系统管理'])
# 学生考核成绩管理模块
app.include_router(router_score, prefix='/score', tags=['学生考核成绩管理'])
# 学生就业管理模块
app.include_router(employment_router, prefix="/Employment", tags=["学生就业信息管理"])
# 班级管理模块
app.include_router(class_router, prefix="/class", tags=["班级管理"])
# 老师管理模块
app.include_router(teacher_information_router, prefix="/teacher", tags=["教师管理"])
# 统计分析模块
app.include_router(sta_router, prefix='/statistics', tags=['统计分析模块'])
# 作业模块
app.include_router(woker, prefix='/work', tags=['作业模块'])
# 邮件模块（调用大模型生成内容并发送邮件）
app.include_router(email_router, prefix='/email', tags=['邮件管理'])
# NL2SQL 智能问数模块
app.include_router(nl2sql_router, prefix='/nl2sql', tags=['NL2SQL智能问数'])
# RAG 四大名著知识库
app.include_router(rag_router,prefix='/rag', tags=['RAG 四大名著知识库'])
# 智能 Agent 助手
app.include_router(agent_router, prefix='/agent', tags=['智能Agent'])

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8088, reload=True)
