from fastapi import FastAPI
import uvicorn
from class_management.API.class_api import class_router

app = FastAPI()

app.include_router(class_router,prefix="",tags=[""])

if __name__ == '__main__':
    uvicorn.run('main:app', host='localhost', port=8088,reload=True)