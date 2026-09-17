from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Query, status
from PIL import UnidentifiedImageError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

import models
from auth import CurrentUser
from config import settings
from database import get_db
from image_utils import delete_image, process_image
from schemas import ExamResponse, ExamCreate, ExamResponse, ExamUpdate, PaginatedExamsResponse

router = APIRouter()

@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_exam(
    exam: ExamCreate, 
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
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
        user_id= current_user.id
    )
    
    db.add(new_exam)
    await db.commit()
    # refresh the exam and load the owner relationship
    await db.refresh(new_exam, attribute_names=["owner"])
    
    return new_exam

# The route get all exams. It wont be used in the future
@router.get("", response_model=PaginatedExamsResponse)
async def get_exams(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.exams_per_page,
):
    # count all the users exams of database
    count_result = await db.execute(
        select(func.count())
        .select_from(models.Exam)
    )
    total = count_result.scalar() or 0
    
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .order_by(models.Exam.date_exam.desc())
        .offset(skip) # skip that many rows
        .limit(limit), # return at most limit exams
    )
    exams = result.scalars().all()
    # fastAPI converts dict into json automaticaly
    
    has_more = skip + len(exams) < total
    
    return PaginatedExamsResponse(
        exams=[ExamResponse.model_validate(exam) for exam in exams],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more
    )

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
async def update_exam_full(
    exam_id: int,
    exam_data: ExamCreate,
    current_user: CurrentUser,
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
    
    if exam.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this exam",
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
    
    await db.commit()
    await db.refresh(exam, attribute_names=["owner"])
    
    return exam

@router.patch("/{exam_id}", response_model=ExamResponse)
async def update_exam_partial(
    exam_id: int,
    exam_data: ExamUpdate,
    current_user: CurrentUser,
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
    
    if exam.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this exam",
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
async def delete_exam(
    exam_id: int, 
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]):
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
    
    if exam.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this exam",
        )
    old_filename = exam.image_file
    
    # exam ownership will come soon
    await db.delete(exam)
    await db.commit()
    
    if old_filename:
        delete_image(old_filename)


######## UPLOADS ##########

@router.patch("/{exam.id}/image", response_model=ExamResponse)
async def upload_exam_image(
    exam_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    
    if exam.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this exam",
        )
    
    content = await file.read()
    # file.size is not always reliable
    # use len to get the size
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size {settings.max_upload_size_bytes // (1024*1024)}MB"
        )
        
    try:
        # Wrap the CPU bound process in a thread
        new_filename = await run_in_threadpool(process_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file. Plese upload a valid image (JPEG, PNG, GIF, WebP)"
        ) from err
    
    old_filename = exam.image_file
    
    exam.image_file = new_filename
    await db.commit()
    await db.refresh(exam)
    
    # delete only if the commit succeeds
    if old_filename:
        delete_image(old_filename)
    
    return current_user

@router.delete("/{exam_id}/image", response_model=ExamResponse)
async def delete_exam_image(
    exam_id: int,
    current_user: CurrentUser,
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
    
    if exam.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this exam",
        )
        
    old_filename = exam.image_file
    
    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No image to delete",
        )

    exam.image_file = None
    await db.commit()
    await db.refresh(exam)
    
    delete_image(old_filename)
    
    return exam