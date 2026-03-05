"""
PDF-Extraktion: liest Text und Formularfelder aus einem PDF.
"""

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_content(file_bytes: bytes) -> tuple[str, list[str]]:
    """
    Extrahiert Text und Formularfeld-Informationen aus einem PDF.

    Args:
        file_bytes: Die Rohdaten der PDF-Datei als Bytes.

    Returns:
        Tuple aus:
        - full_text: Gesamter Textinhalt des PDFs
        - fields_info: Liste mit Informationen zu den Formularfeldern
    """
    reader = PdfReader(BytesIO(file_bytes))

    full_text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + "\n"

    fields_info: list[str] = []
    pdf_fields = reader.get_fields()

    if pdf_fields:
        for field_name, field_data in pdf_fields.items():
            field_type = field_data.get("/FT")
            field_options = field_data.get("/Opt")
            fields_info.append(
                f"Field: '{field_name}', Type: {field_type}, Options: {field_options}"
            )

    return full_text, fields_info
