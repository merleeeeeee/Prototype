"""
Zentrale Konfiguration für die Merged App.

Kombiniert die Konfigurationen beider Ursprungsprojekte:
- pdf_questionnaire_app: LLM-Extraktion aus PDFs
- python_web_app (Wesentlichkeitsanalyse): Wizard + KI-Chat
"""

from enum import Enum
from typing import Final


class QuestionType(str, Enum):
    """Unterstützte Fragetypen im Fragebogen."""

    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    TEXT = "text"


# --- App / Page Config ---
PAGE_TITLE: Final[str] = "Wesentlichkeitsanalyse – KI-gestützt"
PAGE_ICON: Final[str] = "📄"

# --- Navigations-Schritte ---
# -2 = PDF-Upload, -1 = Startseite, 0 = Kontext, 1..N = Fragen, N+1 = Übersicht
STEP_UPLOAD: Final[int] = -2
STEP_START: Final[int] = -1
STEP_CONTEXT: Final[int] = 0

# --- LLM-Einstellungen: Extraktion (aus pdf_questionnaire_app) ---
DEFAULT_CHAT_MODEL: Final[str] = "gpt-oss-120b"
LLM_TEMPERATURE_EXTRACT: Final[float] = 0.0   # Deterministisch für JSON-Ausgabe
MAX_PDF_TEXT_LENGTH: Final[int] = 8000
MAX_FIELDS_TEXT_LENGTH: Final[int] = 4000

# --- LLM-Einstellungen: Chat-Assistent (aus python_web_app) ---
LLM_TEMPERATURE_CHAT: Final[float] = 0.2
LLM_MAX_TOKENS: Final[int] = 2000

# --- PDF-Einstellungen ---
TEMPLATE_PDF_PATH: Final[str] = "pdf_templates/wesentlichkeitsformular.pdf"
FONTS_DIR: Final[str] = "fonts"

PDF_MARGIN: Final[int] = 15
PDF_PAGE_WIDTH: Final[int] = 190
PDF_HEADER_FONT_SIZE: Final[int] = 16
PDF_QUESTION_FONT_SIZE: Final[int] = 12
PDF_ANSWER_FONT_SIZE: Final[int] = 12
PDF_LINE_HEIGHT: Final[int] = 7

# --- System-Prompt: LLM-Extraktion ---
# Erweitert gegenüber dem Original: produziert pdf_yes_no_map und pdf_mc_map
# direkt in den Frage-Objekten, damit kein separates Mapping-File nötig ist.
LLM_EXTRACTION_SYSTEM_PROMPT: Final[str] = """
Du bist ein Experte für Datenextraktion. Deine Aufgabe ist es, aus dem rohen Text eines PDF-Formulars und einer Liste der internen Formularfelder eine strukturierte JSON-Liste für eine Fragebogen-App zu generieren.

Das Zielformat ist eine Liste von Objekten. Jedes Objekt muss EXAKT so aussehen:
{
    "id": "unique_id_string",
    "text": "Der genaue Text der Frage aus dem PDF",
    "type": "single_choice" | "multi_choice" | "text",
    "options": ["Option A", "Option B"],
    "pdf_field_name": "Name des passendsten internen PDF-Feldes oder null",
    "pdf_yes_no_map": {},
    "pdf_mc_map": {}
}

WICHTIGE REGELN:
1. Analysiere den Text logisch. Wenn unter einer Frage Checkboxen stehen, ist es single_choice oder multi_choice.
2. Versuche, die internen 'pdf_field_names' aus der übergebenen Liste den Fragen zuzuordnen. Wenn eine Frage z.B. "Umsetzung als Projekt" heißt und es ein Feld "OptUmsPro" gibt, verknüpfe sie.
3. Ignoriere rein administrative Felder (Datum, Unterschrift, Seitenzahl).
4. Antworte NUR mit dem validen JSON Array, kein Markdown, kein Text davor/danach.
5. Erfasse ALLE Checkbox-Optionen einer Frage, nicht nur die erste!
6. Bei hierarchischen/verschachtelten Strukturen: Fasse Unterpunkte zusammen, z.B.: "Option A (inkl. Unterpunkt 1, Unterpunkt 2)"
7. Achte auf visuelle Strukturen wie Einrückungen, Spiegelstriche (–) und Aufzählungszeichen.
8. Lies den gesamten Textblock einer Frage bis zur nächsten Frage.
9. Eine Antwortmöglichkeit setzt immer eine Checkbox voraus. Wenn keine Checkbox, dann keine Antwortmöglichkeit.

REGELN FÜR PDF-FELD-MAPPINGS (pdf_yes_no_map und pdf_mc_map):
10. Bei single_choice Ja/Nein-Fragen mit einem einzigen PDF-Feld: Befülle "pdf_yes_no_map", z.B.:
    "pdf_field_name": "OptUmsPro",
    "pdf_yes_no_map": {"ja": "1", "nein": "2"},
    "pdf_mc_map": {}

11. Bei multi_choice-Fragen, wo jede Option ein eigenes Checkbox-Feld hat: Befülle "pdf_mc_map", z.B.:
    "pdf_field_name": null,
    "pdf_yes_no_map": {},
    "pdf_mc_map": {
        "Option A": {"field": "OptKategorie",  "value": "1"},
        "Option B": {"field": "OptKategorie1", "value": "1"}
    }

12. Falls du Feldnamen nicht sicher zuordnen kannst, lass die Maps leer ({}). Die App funktioniert auch ohne Mappings.

BEISPIEL für komplexe Fragen:
Wenn du siehst:
"Änderung der Organisation:
☐ Option A
  - mit Bedingung X
☐ Option B"

Dann:
{
    "id": "org_change",
    "text": "Änderung der Organisation",
    "type": "multi_choice",
    "options": ["Option A (mit Bedingung X)", "Option B"],
    "pdf_field_name": null,
    "pdf_yes_no_map": {},
    "pdf_mc_map": {}
}
"""

# --- System-Prompt: KI-Chat-Assistent ---
CHAT_SYSTEM_PROMPT: Final[str] = (
    "Du bist ein hilfreicher Assistent für einen Fragebogen zur "
    "Wesentlichkeitsanalyse in der Nachhaltigkeitsberichterstattung. "
    "Antworte stets kurz, präzise und auf Deutsch. "
    "Beantworte nur Fragen, die inhaltlich mit Wesentlichkeit, Nachhaltigkeit, "
    "Compliance, dem Fragebogen oder den dazugehörigen Begriffen zu tun haben. "
    "Wenn eine Frage offensichtlich nichts damit zu tun hat, erkläre höflich, "
    "dass du nur für Fragen zur Wesentlichkeitsanalyse zuständig bist. "
    "Wenn um Definitionen oder Erklärungen gebeten wird, gib zuerst ein dazu passendes Zitat "
    "aus dem Handbuch aus. "
    "Schreibe dann: \"Für den direkten Link zum Handbuch, klicke *hier*: \""
)
