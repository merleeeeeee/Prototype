"""
PDF-Generierung für die Merged App.

Enthält Funktionen zum Erstellen von:
- Einfachen Übersichts-PDFs mit Fragen und Antworten (fpdf)
- Ausgefüllten Formular-PDFs (pypdf) mit dynamischen Feld-Mappings

Die Feld-Mappings kommen direkt aus den Frage-Objekten (pdf_yes_no_map, pdf_mc_map),
nicht mehr aus einer separaten Mapping-Datei.
"""

import os
from io import BytesIO

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

from .config import FONTS_DIR, PDF_MARGIN, PDF_PAGE_WIDTH
from .config import PDF_HEADER_FONT_SIZE, PDF_QUESTION_FONT_SIZE, PDF_ANSWER_FONT_SIZE, PDF_LINE_HEIGHT


def sanitize_text(text: str) -> str:
    """
    Ersetzt problematische Unicode-Zeichen durch einfache Alternativen.

    Args:
        text: Der zu bereinigende Text

    Returns:
        Bereinigter Text
    """
    if not isinstance(text, str):
        return str(text)

    replacements = {
        "–": "-",
        "—": "-",
        "„": '"',
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "…": "...",
        "•": "-",
        "\u202f": " ",
    }

    cleaned = text
    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)

    return cleaned


def _get_pdf_with_fonts() -> FPDF:
    """Erstellt ein FPDF-Objekt mit den gebündelten DejaVu-Schriftarten."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=PDF_MARGIN)

    font_regular = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    font_bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

    if os.path.exists(font_regular) and os.path.exists(font_bold):
        pdf.add_font("DejaVu", "", font_regular, uni=True)
        pdf.add_font("DejaVu", "B", font_bold, uni=True)
        pdf._font_family = "DejaVu"
        pdf._use_dejavu = True
    else:
        pdf._use_dejavu = False

    return pdf


def _set_font(pdf: FPDF, style: str, size: int) -> None:
    """Setzt die Schriftart (DejaVu wenn verfügbar, sonst Arial)."""
    if getattr(pdf, "_use_dejavu", False):
        pdf.set_font("DejaVu", style, size)
    else:
        pdf.set_font("Arial", style, size)


def generate_answers_pdf(questions: list, answers: dict) -> bytes:
    """
    Erzeugt eine PDF-Übersicht aller Fragen und Antworten.

    Args:
        questions: Liste der Fragen-Dictionaries
        answers: Dictionary mit Antworten (Frage-ID -> Antwort)

    Returns:
        PDF-Datei als Bytes
    """
    pdf = _get_pdf_with_fonts()
    pdf.add_page()

    # Titel
    _set_font(pdf, "B", PDF_HEADER_FONT_SIZE)
    pdf.cell(0, 10, sanitize_text("Übersicht der Antworten"), ln=True)
    pdf.ln(5)

    for idx, q in enumerate(questions, start=1):
        q_text = q.get("text", "")
        ans = answers.get(q["id"], None)

        # Frage
        _set_font(pdf, "B", PDF_QUESTION_FONT_SIZE)
        pdf.multi_cell(0, PDF_LINE_HEIGHT, sanitize_text(f"{idx}. {q_text}"))
        pdf.ln(1)

        # Antwort normalisieren
        _set_font(pdf, "", PDF_ANSWER_FONT_SIZE)
        if isinstance(ans, list):
            ans_str = ", ".join(ans) if ans else "Keine Auswahl getroffen."
        elif isinstance(ans, str):
            ans_str = ans.strip() if ans.strip() else "Keine Antwort eingegeben."
        else:
            ans_str = "Keine Antwort eingegeben."

        pdf.multi_cell(0, PDF_LINE_HEIGHT, sanitize_text(f"Antwort: {ans_str}"))
        pdf.ln(4)

    pdf_output = pdf.output(dest="S")

    if isinstance(pdf_output, str):
        return pdf_output.encode("latin-1")
    return bytes(pdf_output)


def generate_filled_form_pdf(
    template_path: str,
    questions: list,
    answers: dict,
) -> bytes:
    """
    Befüllt das Original-PDF-Formular mit den Antworten.

    Liest die Feld-Mappings direkt aus den Frage-Objekten:
    - pdf_mc_map: Multi-Choice mit je eigenem Checkbox-Feld pro Option
    - pdf_yes_no_map + pdf_field_name: Ja/Nein-Fragen mit Wertemapping
    - pdf_field_name allein: Einfache Text- oder Auswahlfelder

    Args:
        template_path: Pfad zum PDF-Template
        questions: Liste der Fragen-Dictionaries
        answers: Dictionary mit Antworten (Frage-ID -> Antwort)

    Returns:
        Ausgefüllte PDF-Datei als Bytes
    """
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    form_data = {}

    for q in questions:
        q_id = q["id"]
        ans = answers.get(q_id, "")

        # --- 1) Multi-Choice: jede Option hat ihr eigenes PDF-Feld ---
        mc_map = q.get("pdf_mc_map", {})
        if mc_map:
            selected = ans if isinstance(ans, list) else []
            for opt_text, cfg in mc_map.items():
                if opt_text in selected:
                    form_data[cfg["field"]] = cfg["value"]
            continue

        # --- 2) Ja/Nein-Frage mit Wertemapping ---
        field_name = q.get("pdf_field_name")
        yn_map = q.get("pdf_yes_no_map", {})

        if field_name and yn_map and isinstance(ans, str):
            form_data[field_name] = yn_map.get(ans, "")
            continue

        # --- 3) Einfaches Textfeld ---
        if not field_name:
            continue

        if isinstance(ans, list):
            form_data[field_name] = ", ".join(ans)
        elif isinstance(ans, str):
            form_data[field_name] = ans.strip()
        else:
            form_data[field_name] = str(ans)

    for page in writer.pages:
        writer.update_page_form_field_values(page, form_data)

    pdf_buffer = BytesIO()
    writer.write(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    return pdf_bytes
