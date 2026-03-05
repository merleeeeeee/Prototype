"""
Übersichtsseite der Wesentlichkeitsanalyse.

Zeigt alle Antworten und bietet PDF-Downloads an.
Liest die Fragen aus st.session_state.questions (dynamisch extrahiert).
"""

import streamlit as st

from ..config import TEMPLATE_PDF_PATH, STEP_UPLOAD
from ..pdf_generator import generate_answers_pdf, generate_filled_form_pdf


def _get_questions() -> list:
    """Liest die dynamischen Fragen aus dem Session State."""
    return st.session_state.get("questions", [])


def _display_answers(questions: list):
    """Zeigt alle Fragen und Antworten an."""
    for question in questions:
        st.subheader(question["text"])
        ans = st.session_state.answers.get(question["id"], None)

        if isinstance(ans, list):
            st.write(", ".join(ans) if ans else "Keine Auswahl getroffen.")
        elif isinstance(ans, str):
            st.write(ans if ans.strip() else "Keine Antwort eingegeben.")
        else:
            st.write("Keine Antwort eingegeben.")


def _render_action_buttons(questions: list):
    """Rendert die Aktions-Buttons (Zurück, PDF-Downloads)."""
    st.write("Aktionen:")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Letzte Frage bearbeiten"):
            st.session_state.step = len(questions)
            st.rerun()

    with col2:
        summary_pdf_bytes = generate_answers_pdf(questions, st.session_state.answers)
        st.download_button(
            label="Übersicht als PDF herunterladen",
            data=summary_pdf_bytes,
            file_name="wesentlichkeitsanalyse_übersicht.pdf",
            mime="application/pdf",
        )

    with col3:
        try:
            form_pdf_bytes = generate_filled_form_pdf(
                TEMPLATE_PDF_PATH,
                questions,
                st.session_state.answers,
            )
            st.download_button(
                label="Ausgefülltes Original-Formular (Beta)",
                data=form_pdf_bytes,
                file_name="wesentlichkeitsanalyse_formular_ausgefüllt.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Fehler beim Erzeugen des Formular-PDF: {e}")


def render():
    """Rendert die Übersichtsseite."""
    questions = _get_questions()

    st.title("Übersicht Ihrer Antworten")

    _display_answers(questions)

    st.markdown("---")

    _render_action_buttons(questions)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Fragebogen neu starten"):
            st.session_state.step = -1
            st.session_state.answers = {}
            st.session_state.chat_messages = []
            st.rerun()

    with col2:
        if st.button("Neues PDF hochladen"):
            st.session_state.step = STEP_UPLOAD
            st.session_state.questions = []
            st.session_state.answers = {}
            st.session_state.chat_messages = []
            st.rerun()
