# type safe dependecies
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db
from schemas import ExamCreate, ExamResponse, ExamUpdate, UserCreate, UserResponse, UserUpdate

# Create tables if it doesn't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

# # create /static url prefix to serve files from the directory
# app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/media", StaticFiles(directory="media"), name="media")

# Example of a HTMLResponse
@app.get("/", response_class=HTMLResponse, include_in_schema=False, name="home")
@app.get("/exams", response_class=HTMLResponse, include_in_schema=False, name="exams")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Exam))
    exams = result.scalars().all()
    ## fastAPI converts dict in json automaticaly
    # return f"<h1>{exams[0]["name"]}</h1>"
    
    return exams



############################################################
######################## User's API ########################
############################################################

@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
# The get_db injection asks for a session and pass the result to db.
# This happens before the Annotated execution
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    # check if the username exist in the db
    result = db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    # gets the first user object or None if no match found
    existing_user = result.scalars().first()
    
    # Gives exception if the username exists in the database
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    # check if the email exist in the db
    result = db.execute(
        select(models.User).where(models.User.email == user.email),
    )
    # gets the first user object or None if no match found
    existing_email = result.scalars().first()
    
    # Gives exception if the username exists in the database
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
        
    new_user = models.User(
        username=user.username,
        email=user.email
    )
    
    db.add(new_user)
    db.commit()
    # SQLAlchemy maybe alredy track the auto generated ID and relationships.
    # but it is a good habit for server side defaults and triggers
    db.refresh(new_user)
    
    return new_user

@app.get("/api/user/{user_id}", response_model=UserResponse)
def get_users(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    
    user = result.scalars().first()
    
    if user:
        return user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail="User not found",
    )

@app.get("/api/user/{user_id}/exams", response_model=list[ExamResponse])
def get_user_exams(user_id: int, db: Annotated[Session, Depends(get_db)]):
    #check if user exists before try to fetch its exams
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found",
        )
    
    #fetch user's exams
    
    result = db.execute(select(models.Exam).where(models.Exam.user_id == user_id))
    exams = result.scalars().all()
    return exams

@app.patch("/api/user/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[Session, Depends(get_db)]
):
    #check if user exists before try to fetch its exams
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found",
        )
    
    # Check if username alredy exists
    if user_update.username is not None and user_update.username != user.username:
        result = db.execute (
            select(models.User).where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="Username already exists",
                    )
    # Check if e-mail alredy exists
    if user_update.email is not None and user_update.email != user.email:
            result = db.execute (
                select(models.User).where(models.User.email == user_update.email),
            )
            existing_email = result.scalars().first()
            if existing_email:
                raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Email already exists",
                        )
    
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
            user.email = user_update.email
            
    db.commit()
    db.refresh(user)
    return user

@app.delete("/api/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)]
):
    #check if user exists before try to fetch its exams
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found",
        )

    db.delete(user)
    db.commit()
    

############################################################
######################## Exam's API ########################
############################################################

@app.get("/api/exams", response_model=list[ExamResponse])
def get_exams(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Exam))
    exams = result.scalars().all()
    # fastAPI converts dict into json automaticaly
    return exams

@app.get("/api/exam/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.Exam).where(models.Exam.id == exam_id),
    )
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    
    return exam

@app.put("/api/exam/{exam_id}", response_model=ExamResponse)
def update_exam_full(exam_id: int,
             exam_data: ExamCreate,
             db: Annotated[Session, Depends(get_db)]
            ):
    result = db.execute(
        select(models.Exam).where(models.Exam.id == exam_id),
    )
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    
    if exam_data.user_id != exam.user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Users do not match",
        )
    
    exam.area = exam_data.area
    exam.test = exam_data.test
    exam.secction = exam_data.secction
    exam.parameter = exam_data.parameter
    exam.unity = exam_data.unity
    exam.ref_min = exam_data.ref_min
    exam.ref_max = exam_data.ref_max
    exam.result = exam_data.result
    exam.date_exam = exam_data.date_exam
    exam.user_id = exam_data.user_id
    
    db.commit()
    db.refresh(exam)
    
    return exam

@app.patch("/api/exam/{exam_id}", response_model=ExamResponse)
def update_exam_partial(
    exam_id: int,
    exam_data: ExamUpdate,
    db: Annotated[Session, Depends(get_db)]
):
    result = db.execute(
        select(models.Exam).where(models.Exam.id == exam_id),
    )
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    
    # model_dump return a convertion dict from json
    # Exclude fields that aren't set
    update_data = exam_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # setattr is a Python built-in function
        setattr(exam, field, value)
    
    
    db.commit()
    db.refresh(exam)
    
    return exam
    
@app.delete("/api/exam/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.Exam).where(models.Exam.id == exam_id),
    )
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    # exam ownership will come soon
    db.delete(exam)
    db.commit()

@app.post(
    "/api/exams",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED
)
def creat_exam(exam: ExamCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
            select(models.User).where(models.User.id == exam.user_id),
        )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found",
        )
    
    new_exam = models.Exam (
        area= exam.area,
        test= exam.test,
        secction= exam.secction,
        parameter= exam.parameter,
        unity= exam.unity,
        ref_min= exam.ref_min,
        ref_max= exam.ref_max,
        result= exam.result,
        date_exam= exam.date_exam,
        user_id= exam.user_id
    )
    
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    
    return new_exam



############################################################
#################### Exception handlers ####################
############################################################

# catches StarletteHTTPException and reponds with JSONResponse
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message: str = (
        exception.detail
        if exception.detail
        else "An error ocurred. Plese check your request and try again"
    )
    # Respond in JSON if its API or other way if not
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )
    # Here goes a response diferent from JSON, like a temple
    return JSONResponse(
                status_code=exception.status_code,
                content={"detail": "fell into not JSON response"},
            )

# catches RequestValidationError and reponds with JSONResponse
@app.exception_handler(RequestValidationError)
def general_http_exception_handler(request: Request, exception: RequestValidationError):
    # Respond in JSON if its API or other way if not
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
    # Here goes a response diferent from JSON, like a temple
    return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": "fell into not JSON response"},
            )
