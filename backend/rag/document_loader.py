from pathlib import Path
from typing import List, Dict, Any

from pypdf import PdfReader
from docx import Document as DocxDocument

from utils.helpers import clean_text


def extract_text_from_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """Extract text from PDF with page numbers."""
    pages = []
    try:
        reader = PdfReader(str(file_path))
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            text = clean_text(text)
            if text:
                pages.append({"page": i + 1, "text": text})
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    return pages


def extract_text_from_docx(file_path: Path) -> List[Dict[str, Any]]:
    """Extract text from DOCX. Treat paragraphs as continuous text with section markers."""
    try:
        doc = DocxDocument(str(file_path))
        paragraphs = []
        for para in doc.paragraphs:
            t = clean_text(para.text)
            if t:
                paragraphs.append(t)
        full_text = "\n\n".join(paragraphs)
        if not full_text.strip():
            # Also check tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        clean_text(cell.text) for cell in row.cells if cell.text
                    )
                    if row_text:
                        paragraphs.append(row_text)
            full_text = "\n\n".join(paragraphs)
        if not full_text.strip():
            return []
        return [{"page": 1, "text": full_text}]
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")


def extract_text_from_txt(file_path: Path) -> List[Dict[str, Any]]:
    """Extract text from plain text file."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    last_error = None
    for enc in encodings:
        try:
            text = file_path.read_text(encoding=enc)
            text = clean_text(text)
            if not text:
                return []
            return [{"page": 1, "text": text}]
        except Exception as e:
            last_error = e
            continue
    raise ValueError(f"Failed to read text file: {str(last_error)}")


def extract_text(file_path: Path, extension: str) -> List[Dict[str, Any]]:
    """Dispatch extraction based on extension."""
    ext = extension.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext in (".docx", ".doc"):
        # python-docx handles .docx; .doc (old binary) is limited
        if ext == ".doc":
            raise ValueError(
                "Legacy .doc format is not fully supported. Please convert to .docx or PDF."
            )
        return extract_text_from_docx(file_path)
    if ext == ".txt":
        return extract_text_from_txt(file_path)
    raise ValueError(f"Unsupported file type: {ext}")
