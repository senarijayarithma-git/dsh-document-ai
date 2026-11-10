
from pydantic import BaseModel, EmailStr, Field


class EmployeeLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class EmployeeLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmployeeProfileResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
