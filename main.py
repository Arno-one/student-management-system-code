from fastapi import FastAPI
import uvicorn
from API.statistical import sta_router
from API.score_api import router_score
from API.class_api import class_router
from API.student_api import student_router
from API.employment_api import employment_router
from API.teacher_information_API_Router import teacher_information_router

app = FastAPI()

# 学⽣基本信息管理模块
app.include_router(student_router, prefix='/student', tags=['学⽣基本信息管理'])
# 学⽣考核成绩管理模块
app.include_router(router_score, prefix='/score', tags=['学⽣考核成绩管理'])
# 学⽣就业管理模块
app.include_router(employment_router, prefix="/Employment", tags=["学生就业信息管理"])
# 班级管理模块
app.include_router(class_router,prefix="/class",tags=["班级管理"])
# ⽼师管理模块
app.include_router(teacher_information_router,prefix="",tags=["教师管理"])
# 统计分析模块
app.include_router(sta_router, prefix='/statistics', tags=['统计分析模块'])

if __name__ == '__main__':
    uvicorn.run('main:app', host='localhost', port=8088,reload=True)