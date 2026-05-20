from fastapi import FastAPI
import uvicorn
from API.statistical import sta_router
app = FastAPI()

#学⽣基本信息管理模块

#学⽣考核成绩管理模块

#学⽣就业管理模块

# 班级管理模块

#⽼师管理模块

#统计分析模块
app.include_router(sta_router, prefix='/statistics', tags=['统计分析'])

if __name__ == '__main__':
    uvicorn.run('main:app', host='localhost', port=8088,reload=True)