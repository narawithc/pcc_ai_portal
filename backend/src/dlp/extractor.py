import io
import os


def extract_text(filename: str, content: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()

    if ext in (".txt", ".md"):
        return content.decode("utf-8")

    if ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    if ext == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    raise ValueError(f"Unsupported file type: {ext}")
