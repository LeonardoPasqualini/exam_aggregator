from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

# the "+aiosqlite" tells the database which drive to use
# for async process
# SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./exam_agreggator.db"

engine = create_async_engine(
    # connect to postgress
    settings.database_url
    
    # SQLALCHEMY_DATABASE_URL,
    # check_same_thread:false is specific for SQLite,
    # it allows multiple threads to use the same connection.
    # For PostGRESQL, this is not necessary.
    # connect_args={"check_same_thread": False},
)

# Factory for creating new database Session objects
# autocommit=False, autoflush=False are used to control 
# when transactions are committed and when changes are committed to the databas.
# It is a FastAPI standard.
# AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

# Dependecy function to prived sessions to the routes
# Generates a new session for each request
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session