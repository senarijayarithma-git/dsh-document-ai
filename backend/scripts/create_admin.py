from pydantic import EmailStr, TypeAdapter, ValidationError
import getpass
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth_security import hash_password
from app.database import SessionLocal
from app.nmra_models import EmployeeUser

def main():
    print("DSH Document AI - Initial Administrator Setup")

    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(EmployeeUser.id).where(
                EmployeeUser.role == "ADMIN"
            )
        )

        if existing_admin is not None:
            print("An administrator already exists. Setup stopped.")
            return
        email_input = input("Administrator email: ").strip().lower()
        full_name = input("Administrator full name: ").strip()

        try:
            email = str(TypeAdapter(EmailStr).validate_python(email_input))
        except ValidationError:
            print("Please enter a valid administrator email address.")
            return

        if not email or not full_name:
            print("Email and full name are required.")
            return

        existing_user = db.scalar(
            select(EmployeeUser.id).where(
                EmployeeUser.email == email
            )
        )

        if existing_user is not None:
            print("An account with this email already exists.")
            return

        password = getpass.getpass("Administrator password: ")
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

        administrator = EmployeeUser(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="ADMIN",
            is_active=True,
        )

        db.add(administrator)
        db.commit()

        print("Administrator account created successfully.")

if __name__ == "__main__":
    main()
