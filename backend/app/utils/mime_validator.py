import mimetypes
from typing import Any

from fastapi import HTTPException, status

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/msword": [".doc"],
    "text/plain": [".txt"],
}


def validate_mime_type(file_content: bytes, filename: str) -> str:
    if HAS_MAGIC:
        try:
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_buffer(file_content)
        except Exception:
            detected_mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    else:
        detected_mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    
    if not detected_mime or detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {detected_mime or 'unknown'}. Allowed types: {', '.join(ALLOWED_MIME_TYPES.keys())}",
        )
    
    allowed_extensions = ALLOWED_MIME_TYPES[detected_mime]
    file_extension = filename.lower().split(".")[-1] if "." in filename else ""
    
    if file_extension and f".{file_extension}" not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension .{file_extension} does not match detected MIME type {detected_mime}",
        )
    
    return detected_mime
