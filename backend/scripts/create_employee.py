
import getpass
import sys
from pathlib import Path

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth_security import hash_password
from app.database import SessionLocal
from app.nmra_models import EmployeeUser


def main():
    print("DSH Document AI - Employee Account Setup")
    print("Available roles: VIEWER, REVIEWER")

    role = input("Employee role: ").strip().upper()

    if role not in {"VIEWER", "REVIEWER"}:
        print("Invalid role. Choose VIEWER or REVIEWER.")
        return

    email_input = input("Employee email: ").strip().lower()
    full_name = input("Employee full name: ").strip()

    try:
        email = str(TypeAdapter(EmailStr).validate_python(email_input))
    except ValidationError:
        print("Please enter a valid email address.")
        return

    if not full_name:
        print("Full name is required.")
        return

    with SessionLocal() as db:
        existing_user = db.scalar(
            select(EmployeeUser.id).where(
                EmployeeUser.email == email
            )
        )

        if existing_user is not None:
            print("An account with this email already exists.")
            return

        password = getpass.getpass("Employee password: ")
        confirmation = getpass.getpass("Confirm password: ")

        if password != confirmation:
            print("Passwords do not match.")
            return

        if len(password) < 12:
            print("Password must contain at least 12 characters.")
            return

        if len(password) > 128:
            print("Password must not exceed 128 characters.")
            return

        if password.strip() != password:
            print("Password must not begin or end with spaces.")
            return

        employee = EmployeeUser(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )

        try:
            db.add(employee)
            db.commit()
            print(f"{role} account created successfully.")
        except Exception:
            db.rollback()
            print("Account creation failed. No changes were saved.")
            raise


if __name__ == "__main__":
    main()
