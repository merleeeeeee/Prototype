"""
Handbuch-Service: Textextraktion und Definitions-Anreicherung.

Unterstützt PDF, DOCX und TXT als Handbuch-Format.

Vorgehen für Definitionen (handbuch-first):
  Für jede Frage wird der Handbuch-Text vollständig durchgelesen.
  Der LLM prüft Abschnitt für Abschnitt, ob ein Begriff oder Konzept aus dem
  Handbuch in der Frage oder den Antwortoptionen vorkommt oder für ihr
  Verständnis relevant ist. Trifft das zu, wird ein direktes Zitat oder eine
  kurze Zusammenfassung aus dem Handbuch extrahiert.

  Ergebnis: question["help_terms"] = {"Begriff": "Zitat/Zusammenfassung", ...}

Der Handbuch-Volltext wird zusätzlich in st.session_state.handbook_text
gespeichert, damit der Chat-Assistent daraus zitieren kann.
"""

import json
from io import BytesIO
from typing import Any

from openai import OpenAI

from .config import MAX_HANDBOOK_TEXT_LENGTH, LLM_TEMPERATURE_EXTRACT


# ── Textextraktion ─────────────────────────────────────────────────────────────

def extract_handbook_text(file_bytes: bytes, file_name: str) -> str:
    """
    Extrahiert den Rohtext aus einem Handbuch (PDF, DOCX oder TXT).

    Args:
        file_bytes: Dateiinhalt als Bytes
        file_name:  Dateiname (für Typ-Erkennung)

    Returns:
        Extrahierter Text
    """
    ext = file_name.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        return _extract_pdf_text(file_bytes)
    elif ext in ("docx", "doc"):
        return _extract_docx_text(file_bytes)
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Nicht unterstütztes Dateiformat: .{ext}")


def _extract_pdf_text(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(
        page.extract_text() for page in reader.pages if page.extract_text()
    )


def _extract_docx_text(file_bytes: bytes) -> str:
    import docx
    doc = docx.Document(BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


# ── LLM-Definitions-Extraktion ────────────────────────────────────────────────

_DEFINITIONS_PROMPT = """\
Du bist ein Experte für Textanalyse und Wissensextraktion.

Deine Aufgabe:
Du erhältst eine Frage (mit Antwortoptionen) und einen Handbuch-Text.

Lies den Handbuch-Text vollständig und gehe ihn Abschnitt für Abschnitt durch.
Für jeden Abschnitt prüfst du:
  → Kommen Begriffe, Konzepte oder Definitionen aus diesem Abschnitt in der Frage \
oder den Antwortoptionen vor?
  → Oder ist der Abschnitt für das Verständnis dieser Frage inhaltlich relevant?

Wenn ja: Erstelle einen Eintrag:
  "Begriff": "Direktes Zitat aus dem Handbuch (max. 3 Sätze)"

Regeln:
- Zitate IMMER wortgetreu aus dem Handbuch übernehmen, nicht paraphrasieren
- Maximal 4 Einträge pro Frage – nur die wichtigsten
- Wenn kein Abschnitt relevant ist: leeres Objekt {}
- Antworte NUR mit validem JSON, kein Markdown, kein Text davor/danach

Ausgabeformat:
{
  "Begriff A": "Direktes Zitat oder kurze Zusammenfassung aus dem Handbuch.",
  "Begriff B": "..."
}
"""


def _get_definitions_for_question(
    client: OpenAI,
    model: str,
    handbook_text: str,
    question: dict[str, Any],
) -> dict[str, str]:
    """
    Einzelner LLM-Call für eine Frage: handbuch-first Abgleich.

    Returns:
        Dict {Begriff: Zitat/Zusammenfassung} – kann leer sein.
    """
    options_str = ", ".join(question.get("options", [])) or "–"
    truncated   = handbook_text[:MAX_HANDBOOK_TEXT_LENGTH]

    user_prompt = (
        f"Frage: {question.get('text', '')}\n"
        f"Antwortoptionen: {options_str}\n\n"
        f"Handbuch-Text:\n---\n{truncated}\n---\n\n"
        "Gehe den Handbuch-Text jetzt Abschnitt für Abschnitt durch "
        "und extrahiere relevante Begriffe und Zitate für diese Frage."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _DEFINITIONS_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=LLM_TEMPERATURE_EXTRACT,
    )

    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(content)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


def enrich_questions_with_definitions(
    client: OpenAI,
    model: str,
    handbook_text: str,
    questions: list[dict[str, Any]],
    progress_callback=None,
) -> list[dict[str, Any]]:
    """
    Reichert alle Fragen mit Definitionen aus dem Handbuch an.

    Ein LLM-Call pro Frage (handbuch-first Ansatz).
    Ergebnis wird in question["help_terms"] gespeichert.

    Args:
        client:            OpenAI-kompatibler Client
        model:             Modellname
        handbook_text:     Volltext des Handbuchs
        questions:         Liste der Frage-Dicts (werden in-place aktualisiert)
        progress_callback: Optionale Funktion (current, total, question_text)
                           für Fortschrittsanzeige

    Returns:
        Aktualisierte Fragenliste
    """
    total = len(questions)

    for i, q in enumerate(questions):
        if progress_callback:
            progress_callback(i, total, q.get("text", ""))

        q["help_terms"] = _get_definitions_for_question(
            client, model, handbook_text, q
        )

    return questions
