from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import ExamResponse, ExamCreate, ExamResponse, ExamUpdate

router = APIRouter()

@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED
)
async def creat_exam(exam: ExamCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
            select(models.User)
            .options(selectinload(models.Exam.owner))
            .where(models.User.id == exam.user_id),
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
    await db.commit()
    # refresh the exam and load the owner relationship
    await db.refresh(new_exam, attribute_names=["owner"])
    
    return new_exam


@router.get("", response_model=list[ExamResponse])
async def get_exams(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
    )
    exams = result.scalars().all()
    # fastAPI converts dict into json automaticaly
    return exams

@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(exam_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .where(models.Exam.id == exam_id),
    )
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    
    return exam

@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam_full(exam_id: int,
             exam_data: ExamCreate,
             db: Annotated[AsyncSession, Depends(get_db)]
            ):
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .where(models.Exam.id == exam_id),
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
    
    await db.commit()
    await db.refresh(exam, attribute_names=["owner"])
    
    return exam

@router.patch("/{exam_id}", response_model=ExamResponse)
async def update_exam_partial(
    exam_id: int,
    exam_data: ExamUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .where(models.Exam.id == exam_id),
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
    
    
    await db.commit()
    await db.refresh(exam, attribute_names=["owner"])
    
    return exam
    
@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(exam_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .where(models.Exam.id == exam_id),
    )
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    # exam ownership will come soon
    await db.delete(exam)
    await db.commit()

