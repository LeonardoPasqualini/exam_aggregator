from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./exam_agreggator.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # check_same_thread:false is specific for SQLite,
    # it allows multiple threads to use the same connection.
    # For PostGRESQL, this is not necessary.
    connect_args={"check_same_thread": False},
)

# Factory for creating new database Session objects
# autocommit=False, autoflush=False are used to control 
# when transactions are committed and when changes are committed to the databas.
# It is a FastAPI standard.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Dependecy function to prived sessions to the routes
# Generates a new session for each request
def get_db():
    with SessionLocal() as db:
        yield db