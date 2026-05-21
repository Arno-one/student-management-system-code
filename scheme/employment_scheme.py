from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime
class EmploymentCreate(BaseModel):
    student_no: str = Field(...)
    student_name: str = Field(...)
    class_id: int = Field(...)
    job_open_time: Optional[date] = Field(None)
    offer_send_time: Optional[date] = Field(None)
    company_name: Optional[str] = Field(None)
    salary: Optional[int] = Field(None)

class EmploymentUpdate(BaseModel):
    student_no: Optional[str] = Field(None)
    student_name: Optional[str] = Field(None)
    class_id: Optional[int] = Field(None)
    job_open_time: Optional[date] = Field(None)
    offer_send_time: Optional[date] = Field(None)
    company_name: Optional[str] = Field(None)
    salary: Optional[int] = Field(None)

class EmploymentResponse(BaseModel):
    id: int
    student_no: str
    student_name: str
    class_id: int
    job_open_time: Optional[date] = None
    offer_send_time: Optional[date] = None
    company_name: Optional[str] = None
    salary: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True

