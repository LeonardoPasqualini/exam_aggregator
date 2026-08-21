from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)
class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    # allows pydantic to read dot notation, used with
    # models comming from the database
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    # image_file: str | None
    ## Property of user model
    # image_path: str

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
    date_exam: datetime = Field(default_factory=datetime.now)
    
class ExamCreate(ExamBase):
    user_id: int # TEMPORARY

class ExamResponse(ExamBase):
    # allows pydantic to read dot notation, used with
    # model comming from the database
    model_config = ConfigDict(from_attributes=True)
    
    # id: UUID = Field(default_factory=uuid4)
    
    id: int
    user_id: int
    # created_at: datetime
    owner: UserResponse
    
# print(ExamCreate.model_dump_json(ident=2, exclude={some_field}))
