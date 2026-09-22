# for python versions prior of 3.1.4 we need to import annotations
# so we can use classes declared after the call
from __future__ import annotations
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # One to many
    # Backpopulates is used to link to the owner of the exam
    # Allows user.exams for exemple.
    exams: Mapped[list[Exam]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    
class Exam(Base):
    __tablename__ = "exams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    area: Mapped[str] = mapped_column(String(50), nullable=False)
    test: Mapped[str] = mapped_column(String(50), nullable=False)
    secction: Mapped[str] = mapped_column(String(50), nullable=False)
    parameter: Mapped[str] = mapped_column(String(50), nullable=False)
    unity: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_min: Mapped[float] = mapped_column(Float, nullable=True)
    ref_max: Mapped[float] = mapped_column(Float, nullable=True)
    result: Mapped[float] = mapped_column(Float, nullable=False)
    image_file: Mapped[str | None] = mapped_column(
            String(200), 
            nullable=True,
            default=None
        )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    date_exam: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    
    # Many to One
    # Backpopulates is used to link to the owner of the exam
    owner: Mapped[User] = relationship(back_populates="exams")
    
    @property
    def image_path(self) -> str | None:
        if self.image_file:
            return f"/media/exams/{self.image_file}"
        return None
    
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    
    user: Mapped[User] = relationship(back_populates="reset_tokens")