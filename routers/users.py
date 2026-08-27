from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import ExamResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter()

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
# The get_db injection asks for a session and pass the result to db.
# This happens before the Annotated execution
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # check if the username exist in the db
    result = await db.execute(
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
    result = await db.execute(
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
    
    # add the object to the session 
    # it's not a db opperation
    db.add(new_user)
    await db.commit()
    # SQLAlchemy maybe alredy track the auto generated ID and relationships.
    # but it is a good habit for server side defaults and triggers
    await db.refresh(new_user)
    
    return new_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_users(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    
    user = result.scalars().first()
    if user:
        return user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail="User not found",
    )

@router.get("/{user_id}/exams", response_model=list[ExamResponse])
async def get_user_exams(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    #check if user exists before try to fetch its exams
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found",
        )
    
    #fetch user's exams
    
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .where(models.Exam.user_id == user_id))
    exams = result.scalars().all()
    return exams

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    #check if user exists before try to fetch its exams
    result = await db.execute(
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
        result = await db.execute (
            select(models.User)
            .where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="Username already exists",
                    )
    # Check if e-mail alredy exists
    if user_update.email is not None and user_update.email != user.email:
            result = await db.execute (
                select(models.User)
                .where(models.User.email == user_update.email),
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
            
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    #check if user exists before try to fetch its exams
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found",
        )
    # the way delete interact with the section
    # needs await
    await db.delete(user)
    await db.commit()