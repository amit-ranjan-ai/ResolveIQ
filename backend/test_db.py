from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_user"))
        user = result.scalar()

        print("Database connection successful!")
        print("Connected user:", user)

except SQLAlchemyError as error:
    print("Database connection failed!")
    print("Error:", error)
