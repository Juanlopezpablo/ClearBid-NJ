"""Extracción de contenido real, sin API externa."""
from app.services.document_search import extract_search_text, MAX_TEXT

def test_texto_acotado(tmp_path):
    path = tmp_path / "ejemplo.txt"
    path.write_text("x" * (MAX_TEXT + 10))
    assert len(extract_search_text(path, ".txt")) == MAX_TEXT

def test_docx_incluye_tablas(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("Requisitos web")
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "Evidencia en tabla"
    path = tmp_path / "ejemplo.docx"
    doc.save(path)
    text = extract_search_text(path, ".docx")
    assert "Requisitos web" in text and "Evidencia en tabla" in text

def test_pdf_con_texto(tmp_path):
    from PyPDF2 import PdfWriter
    from PyPDF2.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    page = writer.pages[0]
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 100 Td (Evidencia buscable PDF) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / "ejemplo.pdf"
    with path.open("wb") as output:
        writer.write(output)
    assert "Evidencia buscable PDF" in extract_search_text(path, ".pdf")
