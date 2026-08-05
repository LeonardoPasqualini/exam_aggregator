from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse

app = FastAPI()

exams: list[dict] = [
        {
            "id": 1,
            "group": "Hematologia",
            "type": "Hemograma",
            "name": "Eritrócitos",
            "owner": "Leonardo Carvalho",
            "ref_min": 4.30,
            "ref_max": 6.30,
            "result": 5.55,
            "unity": "10^12/l",
            "date": "28/07/2026"
        },
        {
            "id": 2,
            "group": "Hematologia",
            "type": "Hemograma",
            "name": "Hemoglobina",
            "owner": "Leonardo Carvalho",
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

@app.get("/api/exams")
def get_exams():
    # fastAPI converts dict in json automaticaly
    return exams

@app.get("/api/exam/{exam_id}")
def get_exams(exam_id: int):
    for exam in exams:
        if exam.get("id") == exam_id:
            return exam
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")