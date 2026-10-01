# Especial file that pytest recoginizes
# it's used to create fixtures that will be used in the tests
# and envs.

import os
from collections.abc import AsyncGenerator

# points to a test database
# must come before the database imports
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://examuser:exampass@localhost:5432/test_agg"
)
# fake s3, overrides the originals in the .env
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_REGION"] = "us-east-1"

os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database import Base, get_db
from main import app

# allows async, giving a decorator for it
pytest_plugins = ["anyio"]

## Fixture

# scope="session" indicates this function
# runs once for the entiry test session,
# instead of one per test
@pytest.fixture(scope="session")
def anyio_backend():
    # tells anyio which async to use
    return "asyncio"

# create a test database engine
@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool, # disable connection pooling
    )
    return engine

## Setup Database

# all tests will run in a bd transaction
# when the test finish the transaction will be rollback
@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # test runs here
    yield
    # after the tests run, drop the database
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await test_engine.dispose()

# fixture with function scope (default)
# it happens in each test
@pytest.fixture
async def db_session(
    test_engine,
    setup_database,
) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    trans = await conn.begin()

    # bounds with the section and not the engine
    test_async_session = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint", #crate a save point. "fake commit"
    )

    async with test_async_session() as session:
        try:
            # yiels to the test
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()
            
@pytest.fixture
def mocked_aws():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=os.environ["S3_BUCKET_NAME"])
        yield s3
        
@pytest.fixture
async def client(
    db_session: AsyncSession,
    mocked_aws,
) -> AsyncGenerator[AsyncClient]:
    
    async def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        # Asynchronous server gateway interace
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()

### AUTHENTICATION ###

async def create_test_user(
    client: AsyncClient,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> dict:
    response = await client.post(
        "/api/users",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    # The second parameter is for assertion error
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    return response.json()


async def login_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> str:
    response = await client.post(
        "/api/users/token",
        # OAth2 expect form data instead of json
        data={
            "username": email,
            "password": password,
        },
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}