from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ExamBase(BaseModel):
    area: str = Field(min_length=3, max_length=50)
    exam: str = Field(min_length=3, max_length=50)
    secction: str = Field(min_length=3, max_length=50)
    parameter: str = Field(min_length=3, max_length=50)
    unity: str = Field(min_length=1, max_length=20)
    ref_min: float = Field(ge=1)
    ref_max: float = Field(ge=1)
    result: float = Field(ge=1)
    # date: datetime | None = None
    date: str = Field(min_length=1, max_length=50)
    
class ExamCreate(ExamBase):
    pass

class ExamResponse(ExamBase):
    # allows pydantic to read dot notation, used with
    # model comming from the database
    model_config = ConfigDict(from_attributes=True)
    
    # id: UUID = Field(default_factory=uuid4)
    
    id: int
    created_at: datetime = Field(default_factory=datetime.now)
    
# print(ExamCreate.model_dump_json(ident=2, exclude={some_field}))
