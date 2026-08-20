from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime

from schemas import ExamCreate, ExamResponse


app = FastAPI()

exams: list[dict] = [
        {
            "id": 1,
            "area": "Hematologia",
            "exam": "Hemograma",
            "secction": "Eritrograma",
            "parameter": "Eritrócito",
            "owner": "John Smith",
            "unity": "10^12/l",
            "ref_min": 4.30,
            "ref_max": 6.30,
            "result": 5.55,
            "date": "28/07/2026"
        },
        {
            "id": 2,
            "area": "Hematologia",
            "exam": "Hemograma",
            "secction": "Eritrograma",
            "parameter": "Hemoglobina",
            "owner": "John Smith",
            "unity": "g/dl",
            "ref_min": 13.0,
            "ref_max": 16.5,
            "result": 16.0,
            "unity": "g/dl",
            "date": "28/07/2026"
        }
]

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/posts", response_class=HTMLResponse, include_in_schema=False)
def home():
    # fastAPI converts dict in json automaticaly
    return f"<h1>{exams[0]["name"]}</h1>"

@app.get("/api/exams", response_model=list[ExamResponse])
def get_exams():
    # fastAPI converts dict into json automaticaly
    return exams

@app.get("/api/exam/{exam_id}", response_model=ExamResponse)
def get_exams(exam_id: int):
    for exam in exams:
        if exam.get("id") == exam_id:
            return exam
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

@app.post(
    "/api/exams",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED
)
def creat_exam(exam: ExamCreate):
    new_id = max(e["id"] for e in exams) + 1 if exams else 1
    new_exam = {
        "id": new_id,
        "area": exam.area,
        "exam": exam.exam,
        "secction": exam.secction,
        "parameter": exam.parameter,
        "unity": exam.unity,
        "ref_min": exam.ref_min,
        "ref_max": exam.ref_max,
        "result": exam.result,
        "date": "date here"
    }
    
    exams.append(new_exam)
    
    return new_exam

# Exception handlers
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
