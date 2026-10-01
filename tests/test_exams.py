from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient

from image_utils import delete_image
from tests.conftest import auth_header, create_test_user, login_user

valid_exam_json = {
    "area": "Hematologia",
    "test": "Hemograma",
    "secction": "Eritrograma",
    "parameter": "Hemoglobina",
    "unity": "g/dl",
    "ref_min": 13.0,
    "ref_max": 16.5,
    "result": 16.0,
    "date_exam": "2026-09-29T10:01:23.701000Z",
    "image_file": "",
    "image_path": ""
}

# the client parameter is a fixture injection
# pytest serches for fixtures with the same name and inject it in
@pytest.mark.anyio
async def test_get_exams_empty(client: AsyncClient):
    response = await client.get("/api/exams")
    
    assert response.status_code == 200
    data = response.json()
    assert data["exams"] == []
    assert data["total"] == 0
    assert data["has_more"] == False

@pytest.mark.anyio
async def test_get_exams_not_found(client: AsyncClient):
    # starting with a new DB garants that exam 999 does not exist
    response = await client.get("/api/exams/999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Exam not found"
    
@pytest.mark.anyio
async def test_create_exam_success(client: AsyncClient):
    # Auth setup
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/exams",
        json=valid_exam_json,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["area"] == "Hematologia"
    assert data["test"] == "Hemograma"
    assert data["secction"] == "Eritrograma"
    assert data["parameter"] == "Hemoglobina"
    assert data["unity"] == "g/dl"
    assert data["ref_min"] == 13.0
    assert data["ref_max"] == 16.5
    assert data["result"] == 16.0
    assert data["date_exam"] == "2026-09-29T10:01:23.701000Z"
    assert data["image_file"] == None
    assert data["image_path"] == None
    assert data["user_id"] == user["id"]
    assert "id" in data
    assert "created_at" in data
    assert data["owner"]["username"] == "testuser"

@pytest.mark.anyio
async def test_create_exam_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/exams",
        json=valid_exam_json,
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

## Test Update Exam
@pytest.mark.anyio
async def test_update_exam_success(client: AsyncClient):
    # create and authenticate user
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)
    
    # create a valid exam
    response = await client.post(
        "/api/exams",
        json=valid_exam_json,
        headers=headers,
    )
    
    # Update exam
    exam_id = response.json()["id"]
    
    response = await client.patch(
        f"/api/exams/{exam_id}",
        json={"ref_min": 15.0},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["area"] == "Hematologia"
    assert data["test"] == "Hemograma"
    assert data["secction"] == "Eritrograma"
    assert data["parameter"] == "Hemoglobina"
    assert data["unity"] == "g/dl"
    assert data["ref_min"] == 15.0
    assert data["ref_max"] == 16.5
    assert data["result"] == 16.0
    assert data["date_exam"] == "2026-09-29T10:01:23.701000Z"
    
## Test Update Exam Wrong User
@pytest.mark.anyio
async def test_update_exam_wrong_user(client: AsyncClient):
    # create user 1
    await create_test_user(client, username="user1", email="user1@example.com")
    token1 = await login_user(client, email="user1@example.com")
    
    # create exam for user 1
    response = await client.post(
        "/api/exams",
        json=valid_exam_json,
        headers=auth_header(token1)
    )
    exam_id = response.json()["id"]
    
    # create user 2
    await create_test_user(client, username="user2", email="user2@example.com")
    token2 = await login_user(client, email="user2@example.com")
    
    #try to patch user1's exam with user2 token
    response = await client.patch(
        f"/api/exams/{exam_id}",
        json={"ref_min": 15.0},
        headers=auth_header(token2)
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this exam"

## Test Pagination
@pytest.mark.anyio
async def test_get_exams_with_pagination(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)
    
    for i in range(5):
        copied_json = valid_exam_json.copy()
        copied_json["ref_max"] += i 
        response = await client.post(
            "/api/exams",
            json=copied_json,
            headers=headers
        )
        assert response.status_code == 201
        
    response = await client.get("/api/exams")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["exams"]) == 5
    assert data["has_more"] is False
    
    response = await client.get("/api/exams?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["exams"]) == 2
    assert data["has_more"] is True

    response = await client.get("/api/exams?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["exams"]) == 2
    assert data["skip"] == 2


## Test upload file
@pytest.mark.anyio
async def test_upload_exam_image(client: AsyncClient, mocked_aws):
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)
    
    response = await client.post(
        "/api/exams",
        json=valid_exam_json,
        headers=headers,
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # read the test image from disk
    test_image_path = Path(__file__).parent / "test_image.jpg"
    image_bytes = test_image_path.read_bytes()
    
    response = await client.patch(
        f"/api/exams/{data["id"]}/image",
        # file name, file content, file type
        files={"file": ("exam.jpg", BytesIO(image_bytes), "image/jpeg")},
        headers=auth_header(token),
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["image_file"] is not None
    assert data["image_file"].endswith(".jpg")
    
    delete_image(data["image_file"])
    ## For s3
    # assert "s3" in data["image_path"]
    
    # s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
    # assert "Contents" in s3_objects
    # assert len(s3_objects["Contents"]) == 1
    # assert s3_objects["Contents"][0]["Key"].endswith(data["image_file"])
    