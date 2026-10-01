from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_user


## Validation Tests
@pytest.mark.anyio
async def test_crete_user_validation_error(client: AsyncClient):
    # lacks email and password
    response = await client.post(
        "/api/users",
        json={
            "username": "testuser",
        }
    )
    
    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.text
    
# Test USer duplicated email
@pytest.mark.anyio
async def test_create_user_duplicated_email(client: AsyncClient):
    await create_test_user(client)
    
    response = await client.post(
        "/api/users",
        json={
            "username": "diferent_user",
            "email": "test@example.com",
            "password": "password123",
        }
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exists"
    
## Test Create user Success
@pytest.mark.anyio
async def test_create_user_success(client: AsyncClient):
    response = await client.post(
        "/api/users",
        json={
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "securepassword123",
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_user"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data
    
## Test resetpassword
@pytest.mark.anyio
async def test_forgot_password_sends_email(client: AsyncClient):
    await create_test_user(client)
    
    # context manager mock to temporall replace
    # the mailer with AsyncMock
    # send_password_reset_email lives in the email_utils
    #  patch where the name is looked up and not where is defined
    with patch(
        "routers.users.send_password_reset_email",
        new_callable=AsyncMock,
    ) as mock_send:
        response = await client.post(
            "/api/users/forgot-password",
            json={"email": "test@example.com"},
        )
        
        assert response.status_code == 202
        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to_email"] == "test@example.com"
        assert call_kwargs["username"] == "testuser"
        assert "token" in call_kwargs