"""
Merged App – Hauptanwendung

Kombiniert PDF-Extraktion (pdf_questionnaire_app) mit dem Wizard + KI-Chat
(python_web_app / Wesentlichkeitsanalyse).

Ablauf:
  Step -2  →  PDF hochladen, KI extrahiert Fragen
  Step -1  →  Startseite (Bestätigung + Einstieg)
  Step  0  →  Projektkontext (optional)
  Step 1..N →  Fragen-Wizard mit KI-Chat-Assistent
  Step >N  →  Übersicht + PDF-Download

Starten mit:
    streamlit run app.py
"""

import streamlit as st

from src.config import PAGE_TITLE, PAGE_ICON, STEP_UPLOAD, STEP_START, STEP_CONTEXT
from src.pages import upload_page, start_page, context_page, question_page, summary_page


st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")


def init_session_state():
    """Initialisiert den Session State mit Standardwerten."""
    defaults = {
        "step":            STEP_UPLOAD,  # Startet beim PDF-Upload (-2)
        "questions":       [],           # Dynamisch extrahierte Fragen
        "answers":         {},
        "project_context": "",
        "chat_messages":   [],
        "uploaded_pdf":    None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def main():
    """Hauptfunktion – Router für die verschiedenen Seiten."""
    init_session_state()

    step = st.session_state.step
    questions = st.session_state.get("questions", [])

    if step == STEP_UPLOAD:          # -2: PDF hochladen
        upload_page.render()

    elif step == STEP_START:         # -1: Startseite
        start_page.render()

    elif step == STEP_CONTEXT:       # 0: Projektkontext
        context_page.render()

    elif 1 <= step <= len(questions):  # 1..N: Fragen
        question_page.render(step - 1)

    else:                            # >N: Übersicht
        summary_page.render()


if __name__ == "__main__":
    main()
