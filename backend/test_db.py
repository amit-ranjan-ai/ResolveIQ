from sqlalchemy import text

from app.db.session import engine


try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database(), current_user"))
        database, user = result.fetchone()

        print("Database connection successful!")
        print("Database:", database)
        print("Connected user:", user)

except Exception as error:
    print("Database connection failed!")
    print("Error:", error)

finally:
    engine.dispose()