"""Extracción local acotada: sin servicios de IA ni envío de documentos a terceros."""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

from app.services.storage import get_storage, KEY_RE

logger = logging.getLogger(__name__)
MAX_TEXT = 1_000_000
TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml", ".xml", ".sql", ".toml", ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".cs", ".rb", ".go", ".rs", ".php", ".swift", ".kt", ".scala"}

def extract_search_text(path, extension):
    if extension == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        if len(reader.pages) > 500:
            raise ValueError("PDF demasiado extenso")
        parts, size = [], 0
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
            size += len(text)
            if size >= MAX_TEXT:
                break
        return "\n".join(parts)[:MAX_TEXT]
    if extension == ".docx":
        # Evitar archivos comprimidos que se expandan sin límite.
        with ZipFile(path) as archive:
            if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                raise ValueError("Documento expandido demasiado grande")
        from docx import Document
        doc = Document(path)
        parts = [item.text for item in doc.paragraphs]
        parts.extend(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
        return "\n".join(parts)[:MAX_TEXT]
    with open(path, encoding="utf-8", errors="replace") as stream:
        return stream.read(MAX_TEXT)

async def index_document(document):
    extension = Path(document.filename).suffix.lower()
    document.search_text = None
    if extension not in TEXT_EXTENSIONS | {".pdf", ".docx"}:
        document.search_status = "unsupported"
        return
    if not KEY_RE.match(document.file_path or ""):
        document.search_status = "unavailable"
        return
    fd, path = tempfile.mkstemp(suffix=extension)
    os.close(fd)
    try:
        storage = get_storage()
        size = await storage.size(document.file_path)
        if size is None or size > 25 * 1024 * 1024:
            document.search_status = "unavailable"
            return
        await storage.download_to(document.file_path, path)
        text = await asyncio.to_thread(extract_search_text, path, extension)
        text = text.replace("\x00", "")
        document.search_text = text or None
        document.search_status = "ready" if text.strip() else "empty"
    except Exception:
        logger.warning("No se pudo indexar el documento %s", document.id)
        document.search_status = "error"
    finally:
        Path(path).unlink(missing_ok=True)
