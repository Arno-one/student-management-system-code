from fastapi import FastAPI
import uvicorn
app = FastAPI()

#学⽣基本信息管理模块

#学⽣考核成绩管理模块

#学⽣就业管理模块

# 班级管理模块

#⽼师管理模块

#统计分析模块

if __name__ == '__main__':
    uvicorn.run('main:app', host='localhost', port=8088,reload=True)