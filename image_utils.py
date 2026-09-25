import uuid
import boto3

from io import BytesIO
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from PIL import Image, ImageOps
from config import settings

IMG_DIR = Path("media/exams")

# Pillow is cpu bound, not async. So it will block the event loop

def process_image(content: bytes) -> Image:
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)
        
        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)
        
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        
        return img
    
# LOCAL FILE FUNCTIONS
def save_in_local_files(content: bytes) -> str:
    img = process_image(content)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = IMG_DIR / filename
    
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    
    img.save(filepath, "JPEG", quality=85, optimize=True)
    
    return filename
    
def delete_image(filename: str | None) -> None:
    if filename in None:
        return
    
    filepath = IMG_DIR / filename
    if filepath.exists():
        # pathlib way to delete
        filepath.unlink()


# S3 FUNCTIONS
def _get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=(
            settings.s3_access_key_id.get_secret_value()
            if settings.s3_access_key_id
            else None
        ),
        aws_secret_access_key=(
            settings.s3_access_key_id.get_secret_value()
            if settings.s3_access_key_id
            else None
        ),
        endpoint_url=settings.s3_endpoint_url,
    )
    
def save_in_s3(content: bytes) -> tuple[bytes, str]:
    img = process_image(content)
    
    filename = f"{uuid.uuid4().hex}.jpg"
    
    # in memory file
    output = BytesIO()
    img.save(output, "JPEG", quality=85, optimize=True)
    # go back to first byte
    output.seek(0)
    
    return output.read(), filename

def _upload_to_s3(file_bytes: bytes, key: str) -> None:
    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )
    
def _delete_from_s3(key: str) -> None:
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)

async def upload_s3_exam_image(file_bytes: bytes, filename: str) -> None:
    # the key is the directory/filename in the S3
    key = f"exams/{filename}"
    await run_in_threadpool(_upload_to_s3, file_bytes, key)
    
async def delete_s3_exam_image(filename: str | None) -> None:
    if filename is None:
        return
    # the key is the directory/filename in the S3
    key = f"exams/{filename}"
    await run_in_threadpool(_delete_from_s3, key)