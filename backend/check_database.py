from sqlalchemy import text

from app.database import engine


def main() -> None:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database(), current_user")).one()
    print(f"Database connection OK: database={result[0]}, user={result[1]}")


if __name__ == "__main__":
    main()
