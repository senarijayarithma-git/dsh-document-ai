import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hasher.verify(
        plain_password,
        hashed_password,
    )

load_dotenv()

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 30


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or too short."
        )

    return secret


def create_access_token(employee_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(employee_id),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=JWT_EXPIRY_MINUTES),
        "type": "access",
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "nbf", "exp"]},
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type.")

    employee_id = payload["sub"]

    if (
        not isinstance(employee_id, str)
        or not employee_id.isdecimal()
        or int(employee_id) < 1
    ):
        raise jwt.InvalidTokenError("Invalid employee ID.")

    return int(employee_id)
