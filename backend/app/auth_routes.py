
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.nmra_models import EmployeeUser
from app.auth_schemas import (
    EmployeeLoginRequest,
    EmployeeLoginResponse,
    EmployeeProfileResponse,
)
from app.auth_security import (
    create_access_token,
    verify_password,
)
from app.auth_dependencies import get_current_employee
from app.login_rate_limit import check_login_rate_limit


router = APIRouter(
    prefix="/auth",
    tags=["Employee Authentication"],
)


@router.post(
    "/login",
    response_model=EmployeeLoginResponse,
)
def employee_login(
    request: EmployeeLoginRequest,
    db: Session = Depends(get_db),
    _: None = Depends(check_login_rate_limit),
):
    email = str(request.email).strip().lower()

    employee = db.scalar(
        select(EmployeeUser).where(
            EmployeeUser.email == email
        )
    )

    if (
        employee is None
        or not employee.is_active
        or not verify_password(
            request.password,
            employee.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(employee.id)

    return EmployeeLoginResponse(
        access_token=token,
    )


@router.get(
    "/me",
    response_model=EmployeeProfileResponse,
)
def get_my_profile(
    employee: EmployeeUser = Depends(get_current_employee),
):
    return employee
