from pydantic import BaseModel, ConfigDict, Field

class ExamBase(BaseModel):
    id: int = Field(ge=1)
    area: str = Field(min_length=3, max_length=50)
    exam: str = Field(min_length=3, max_length=50)
    secction: str = Field(min_length=3, max_length=50)
    parameter: str = Field(min_length=3, max_length=50)
    unity: str = Field(min_length=1, max_length=20)
    ref_min: int = Field(ge=1)
    ref_max: int = Field(ge=1)
    result: int = Field(ge=1)
    date: str = Field(min_length=10, max_length=1)
    
class ExamCreate(ExamBase):
    pass

class ExamResponse(ExamBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: str