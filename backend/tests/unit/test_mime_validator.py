import pytest
from fastapi import HTTPException

from app.utils.mime_validator import ALLOWED_MIME_TYPES, validate_mime_type


@pytest.mark.unit
class TestValidateMimeType:
    def test_accepts_pdf_with_pdf_extension(self):
        content = b"%PDF-1.4 fake pdf content"
        result = validate_mime_type(content, "document.pdf")
        assert result == "application/pdf"

    def test_accepts_txt_extension_for_plain_text(self):
        content = b"plain text content"
        result = validate_mime_type(content, "readme.txt")
        assert result == "text/plain"

    def test_rejects_unsupported_mime_type(self):
        content = b"binary content"
        with pytest.raises(HTTPException) as exc_info:
            validate_mime_type(content, "script.exe")
        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert "Unsupported file type" in detail or "does not match" in detail or ".exe" in detail

    def test_rejects_extension_mismatch_for_allowed_mime(self):
        content = b"%PDF-1.4 fake"
        with pytest.raises(HTTPException) as exc_info:
            validate_mime_type(content, "document.docx")
        assert exc_info.value.status_code == 400
        assert "does not match" in exc_info.value.detail or "extension" in exc_info.value.detail.lower()

    def test_allowed_mime_types_defined(self):
        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert "text/plain" in ALLOWED_MIME_TYPES
