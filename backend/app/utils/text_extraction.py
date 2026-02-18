from pathlib import Path
from typing import List, Tuple

import fitz
from docx import Document as DocxDocument


def extract_pdf_text(file_path: Path) -> List[Tuple[int, str]]:
    document = fitz.open(file_path)
    pages: List[Tuple[int, str]] = []
    for index in range(len(document)):
        page = document.load_page(index)
        text = page.get_text()
        if text.strip():
            pages.append((index + 1, text))
    document.close()
    return pages


def extract_docx_text(file_path: Path) -> List[Tuple[int, str]]:
    document = DocxDocument(str(file_path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    if not paragraphs:
        return []
    text = "\n\n".join(paragraphs)
    return [(1, text)]


def extract_txt_text(file_path: Path) -> List[Tuple[int, str]]:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if not content.strip():
        return []
    return [(1, content)]

