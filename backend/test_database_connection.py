
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import engine


def main():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_user, current_database()")
            )

            row = result.fetchone()

            print("DATABASE CONNECTION SUCCESSFUL!")
            print("Connected user:", row[0])
            print("Database:", row[1])

    except OperationalError as error:
        print("DATABASE CONNECTION FAILED!")

        # Print only the PostgreSQL driver's error message.
        # Avoid displaying the database connection URL.
        original_error = error.orig
        message = str(original_error)

        # Remove any lines that might contain connection strings.
        safe_lines = [
            line
            for line in message.splitlines()
            if "password=" not in line.lower()
            and "postgresql://" not in line.lower()
            and "postgresql+psycopg://" not in line.lower()
        ]

        print("\n".join(safe_lines))

    except Exception as error:
        print("Unexpected error:", type(error).__name__)


if __name__ == "__main__":
    main()

