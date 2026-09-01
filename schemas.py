from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)
class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=120)


class Token(BaseModel):
    access_token: str
    token_type: str
class UserPublic(BaseModel):
    # allows pydantic to read dot notation, used with
    # models comming from the database
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    # image_file: str | None
    ## Property of user model
    # image_path: str

class UserPrivate(UserPublic):
    email: EmailStr

class ExamBase(BaseModel):
    area: str = Field(min_length=3, max_length=50)
    test: str = Field(min_length=3, max_length=50)
    secction: str = Field(min_length=3, max_length=50)
    parameter: str = Field(min_length=3, max_length=50)
    unity: str = Field(min_length=1, max_length=20)
    ref_min: float = Field(ge=1)
    ref_max: float = Field(ge=1)
    result: float = Field(ge=1)
    # date: datetime | None = None
    date_exam: datetime
    
class ExamCreate(ExamBase):
    user_id: int # TEMPORARY
    
class ExamUpdate(BaseModel):
    area: str | None = Field(default=None, min_length=3, max_length=50)
    test: str | None = Field(default=None, min_length=3, max_length=50)
    secction: str | None = Field(default=None, min_length=3, max_length=50)
    parameter: str | None = Field(default=None, min_length=3, max_length=50)
    unity: str | None = Field(default=None, min_length=1, max_length=20)
    ref_min: float | None = Field(default=None, ge=1)
    ref_max: float | None = Field(default=None, ge=1)
    result: float | None = Field(default=None, ge=1)
    date_exam: datetime | None = Field(default=None)

class ExamResponse(ExamBase):
    # allows pydantic to read dot notation, used with
    # model comming from the database
    model_config = ConfigDict(from_attributes=True)
    
    # id: UUID = Field(default_factory=uuid4)
    
    id: int
    user_id: int
    created_at: datetime = Field(default_factory=datetime.now)
    owner: UserPublic
    
# print(ExamCreate.model_dump_json(ident=2, exclude={some_field}))
