from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
# 数据库连接信息统一从 config（.env）读取，不再硬编码在代码里
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

user = DB_USER
password = DB_PASSWORD
host = DB_HOST
port = DB_PORT
database = DB_NAME

engine = create_engine(
    f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
    pool_size=5
)

# 创建基类
Base = declarative_base()

# 创建会话工厂
Session = sessionmaker(bind=engine)


# 生成会话
def get_db():
    db = Session()
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
    Base.metadata.create_all(engine)