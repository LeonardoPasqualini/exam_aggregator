import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

IMG_DIR = Path("media/exams")

# Pillow is cpu bound, not async. So it will block the event loop

def process_image(content: bytes) -> str:
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)
        
        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)
        
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
            
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