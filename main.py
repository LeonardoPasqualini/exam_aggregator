from contextlib import asynccontextmanager
# type safe dependecies
from typing import Annotated

from fastapi import FastAPI, Request, status, Depends
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import models
from database import engine, get_db

from routers import exams, users

## Create tables if it doesn't exist
## removed for async update
# Base.metadata.create_all(bind=engine)

# Create tables if it doesn't exist async
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    # async with engine.begin() as conn:
        # create_all looks to the models 
        # and crate tables if not exists, even if it has changes
        # it's not a migration
        # await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

# # create /static url prefix to serve files from the directory
# app.mount("/static", StaticFiles(directory="static"), name="static")

# remove this if working with s3
app.mount("/media", StaticFiles(directory="media"), name="media")

# The list tags organizes the documentation in a collapsable secction
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])

# Example of a HTMLResponse
@app.get("/", response_class=HTMLResponse, include_in_schema=False, name="home")
@app.get("/exams", response_class=HTMLResponse, include_in_schema=False, name="exams")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Exam).options(selectinload(models.Exam.owner)),
    )
    exams = result.scalars().all()
    ## fastAPI converts dict in json automaticaly
    # return f"<h1>{exams[0]["name"]}</h1>"
    
    return exams

############################################################
#################### Exception handlers ####################
############################################################

# catches StarletteHTTPException and reponds with JSONResponse
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    # message: str = (
    #     exception.detail
    #     if exception.detail
    #     else "An error ocurred. Plese check your request and try again"
    # )
    # Respond in JSON if its API or other way if not
    if request.url.path.startswith("/api"):
        # return JSONResponse(
        #     status_code=exception.status_code,
        #     content={"detail": message},
        # )
        
        # with async it's better let Fast API handle the error
        return await http_exception_handler(request, exception)
    # Here goes a response diferent from JSON, like a templete route
    return JSONResponse(
                status_code=exception.status_code,
                content={"detail": "fell into not JSON response"},
            )

# catches RequestValidationError and reponds with JSONResponse
@app.exception_handler(RequestValidationError)
async def general_http_exception_handler(request: Request, exception: RequestValidationError):
    # Respond in JSON if its API or other way if not
    if request.url.path.startswith("/api"):
        # return JSONResponse(
        #     status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        #     content={"detail": exception.errors()},
        # )
        return await request_validation_exception_handler(request, exception)
    # Here goes a response diferent from JSON, like a temple
    return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": "fell into not JSON response"},
            )
