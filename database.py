from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
# 数据库连接信息统一从 config（.env）读取，不再硬编码在代码里
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, \
    DB_READONLY_USER, DB_READONLY_PASSWORD
from util.log import register_sqlalchemy_sql_logging

user = DB_USER
password = DB_PASSWORD
host = DB_HOST
port = DB_PORT
database = DB_NAME

# 读写引擎
engine = create_engine(
    f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
    pool_size=5
)
register_sqlalchemy_sql_logging(engine, "rw")

# 只读引擎 — NL2SQL 专用
# 优先使用只读账号；未配置时回退到读写账号（兼容开发环境，但生产环境建议配置独立只读账号）
_readonly_user = DB_READONLY_USER or user
_readonly_password = DB_READONLY_PASSWORD or password

engine_readonly = create_engine(
    f'mysql+pymysql://{_readonly_user}:{_readonly_password}@{host}:{port}/{database}',
    pool_size=3,
    execution_options={"isolation_level": "READ COMMITTED"}
)
register_sqlalchemy_sql_logging(engine_readonly, "readonly")

# 创建基类
Base = declarative_base()

# 创建会话工厂
Session = sessionmaker(bind=engine)
SessionReadonly = sessionmaker(bind=engine_readonly)


# 生成读写会话
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


# 生成只读会话 — NL2SQL 查询专用
def get_db_readonly():
    db = SessionReadonly()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表结构 — 在应用启动时调用一次"""
    # 导入所有Model以确保它们被注册到Base.metadata
    import model.Student  # noqa: F401
    import model.Class  # noqa: F401
    import model.Score  # noqa: F401
    import model.Employment  # noqa: F401
    import model.Teacher  # noqa: F401
    import model.Talk  # noqa: F401
    import model.NL2SQL  # noqa: F401
    import model.Auth  # noqa: F401
    Base.metadata.create_all(engine)
