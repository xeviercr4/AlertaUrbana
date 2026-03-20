"""Document processing: text extraction and chunking."""
import io
import re
from pathlib import Path


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode plain text, trying UTF-8 then latin-1 as fallback."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def extract_text(file_bytes: bytes, file_ext: str) -> str:
    """Dispatch extraction by file extension."""
    ext = file_ext.lower().lstrip(".")
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == "docx":
        return extract_text_from_docx(file_bytes)
    elif ext == "txt":
        return extract_text_from_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def clean_text(text: str) -> str:
    """Remove excessive whitespace and blank lines."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks measured in words.

    Args:
        text: Input text to chunk.
        chunk_size: Maximum number of words per chunk.
        overlap: Number of words to overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


def process_document(file_bytes: bytes, filename: str) -> list[str]:
    """
    Full pipeline: extract text → clean → chunk.

    Returns list of text chunks ready for embedding.
    """
    ext = Path(filename).suffix
    raw_text = extract_text(file_bytes, ext)
    cleaned = clean_text(raw_text)
    return chunk_text(cleaned)
