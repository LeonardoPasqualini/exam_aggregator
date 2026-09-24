from datetime import timedelta, UTC, datetime
from typing import Annotated

from argon2 import verify_password
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_passoword,
    generate_reset_tokens,
    hash_reset_token
)

from email_utils import send_password_reset_email
from config import settings
from database import get_db
from schemas import (
    ExamResponse,
    PaginatedExamsResponse,
    UserCreate,
    UserUpdate,
    UserPrivate,
    UserPublic,
    Token,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)

router = APIRouter()

@router.post(
    "",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED
)
# The get_db injection asks for a session and pass the result to db.
# This happens before the Annotated execution
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # check if the username exist in the db
    result = await db.execute(
        select(models.User).where(
            # the func is used to make the query case insensitive
            func.lower(models.User.username) == user.username.lower()
        ),
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
        select(models.User).where(
            func.lower(models.User.email) == user.email.lower()),
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
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )
    
    # add the object to the session 
    # it's not a db opperation
    db.add(new_user)
    await db.commit()
    # SQLAlchemy maybe alredy track the auto generated ID and relationships.
    # but it is a good habit for server side defaults and triggers
    await db.refresh(new_user)
    
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "Username" field, but we treat it as email
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    
    user = result.scalars().first()
    
    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_passoword(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer")

# Endpoit to get current user
@router.get("/me", response_model=UserPrivate)
async def get_current_user(current_user: CurrentUser):
    return current_user

@router.post("/forgot-passowrd", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == request_data.email.lower()
        )
    )
    user = result.scalars().first()
    
    if user:
        # delete existing reset token from the user
        await db.execute(
            sql_delete(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id
            )
        )
        # generete new valid token
        token = generate_reset_tokens()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes
        )
        # creates a new db PasswordResetToken
        reset_token = models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.add(reset_token)
        await db.commit()
        # schedule email to be send in the background
        # the backgroud task executes after,
        # so the db session may alredy be closed
        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token # not hashed. It will be used by the user
        )
    
    # Message given always to avoid email enumeration attacks
    return {
        "message": "If an account exists with this email, you will recive password reset instructions."
    }
    
@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    token_hash = hash_reset_token(request_data.token)
    
    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash
        )
    )
    reset_token = result.scalars().first()
    
    if not reset_token:
        raise HTTPException(
            statu_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
        
    result = await db.execute(
        select(models.User).where(models.User.id == reset_token.user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            statu_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user.password_hash = hash_password(request_data.new_password)
    
    # invalidates all standing tokens
    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id
        )
    )
    
    await db.commit()
    return {
        "message": "Password reset successfully. You can now log in with your new password."
    }
    

@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(password_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == current_user.id,
        ),
    )

    await db.commit()
    return {"message": "Password changed successfully"}

@router.get("/{user_id}", response_model=UserPublic)
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

@router.get("/{user_id}/exams", response_model=PaginatedExamsResponse)
async def get_user_exams(
    user_id: int, 
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.exams_per_page
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
    
    #fetch user's exams
    
    count_result = await db.execute(
        select(func.count())
        .select_from(models.Exam)
        .where(models.Exam.user_id == user_id),
    )
    
    total = count_result.scalar() or 0
    
    result = await db.execute(
        select(models.Exam)
        .options(selectinload(models.Exam.owner))
        .where(models.Exam.user_id == user_id)
        .order_by(models.Exam.date_exam.desc())
        .offset(skip)
        .offset(limit),
    )
    exams = result.scalars().all()
    has_more = skip + len(exams) < total
    return PaginatedExamsResponse(
        exams=[ExamResponse.model_validate(exam) for exam in exams],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more
    )

@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
        
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
    if user_update.username.lower() is not None and user_update.username.lower() != user.username.lower():
        result = await db.execute (
            select(models.User)
            .where(
                func.lower(models.User.username) == user_update.username.lower()),
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
                .where(
                    func.lower(models.User.email) == user_update.email.lower()),
            )
            existing_email = result.scalars().first()
            if existing_email:
                raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Email already exists",
                        )
    
    if user_update.username.lower() is not None:
        user.username = user_update.username.lower()
    if user_update.email is not None:
            user.email = user_update.email.lower()
            
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )
        
    # check if user exists before try to fetch its exams
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