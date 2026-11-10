import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.nmra_models import EmployeeUser
from app.auth_security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_employee(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> EmployeeUser:

    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise authentication_error

    try:
        employee_id = decode_access_token(
            credentials.credentials
        )
    except (jwt.InvalidTokenError, ValueError):
        raise authentication_error

    employee = db.get(EmployeeUser, employee_id)

    if employee is None or not employee.is_active:
        raise authentication_error

    return employee


def require_nmra_reviewer(
    employee: EmployeeUser = Depends(get_current_employee),
) -> EmployeeUser:

    if employee.role not in {"ADMIN", "REVIEWER"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NMRA reviewer permission required.",
        )

    return employee
