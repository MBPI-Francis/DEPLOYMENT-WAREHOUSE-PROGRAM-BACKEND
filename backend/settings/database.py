from sqlalchemy import create_engine
from sqlalchemy.orm import  sessionmaker, declarative_base
# from sqlalchemy.ext.declarative import declarative_base
import psycopg2

# The DATABASE_URL variable is the connection string (also known as a database URL) used to specify how to connect to your PostgreSQL database.

# Uncomment this if you want to use the RMDummyDB Database. This is the database for development
# DATABASE_URL = "postgresql://postgres:mbpi@192.168.1.13:5432/RMDummyDB"

# Uncomment this if you want to use the RMManagementSystemDB Database. This is the database for deployment
# DATABASE_URL = "postgresql://postgres:mbpi@192.168.1.13:5432/RMManagementSystemDB"

# Uncomment this if you want to use the RMManagementSystemDB Database in your own computer/laptop. This is the database for development
DATABASE_URL = "postgresql://postgres:331212@localhost:5432/RMManagementSystemDB"

# This url is for sir Elton. You can uncomment  (With Password)
# DATABASE_URL = "postgresql://postgres:newpassword@localhost:5432/RMManagementSystemDB"

# This url is for sir Elton. You can uncomment this (Without Password)
# DATABASE_URL = "postgresql://postgres@localhost:5432/RMManagementSystemDB"


# The engine is responsible for managing low-level details like connecting to
# the database and executing raw SQL commands.
engine = create_engine(DATABASE_URL)

# SssionLocal allows you to interact with the database in an organized and transactional way.
# Each request typically gets its own session instance.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Every model (table) in SQLAlchemy must extend this Base class.
# It provides SQLAlchemy with the metadata to map Python classes to database tables.
Base = declarative_base()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



