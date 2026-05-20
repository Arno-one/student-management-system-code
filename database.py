from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker

user= 'root'
password = '123456'
host = 'localhost'
port= '3306'
database = 'student_management_system'

engine = create_engine(
    f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
    pool_size =5
)

#创建基类
Base = declarative_base()

#创建会话工厂
Session = sessionmaker(bind=engine)

#生成会话
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()