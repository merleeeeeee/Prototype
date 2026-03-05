"""
Upload-Seite: PDF hochladen und Fragen via LLM extrahieren.

Dies ist der neue erste Schritt der Merged App.
Das extrahierte Fragen-Array wird in st.session_state.questions gespeichert
und ersetzt die früher hartcodierten QUESTIONS aus questions.py.
"""

import streamlit as st

from ..pdf_extractor import extract_pdf_content
from ..llm_extraction import get_llm_client_for_extraction, analyze_pdf_with_llm
from ..config import STEP_START


def render():
    """Rendert die Upload-Seite."""
    st.title("📄 Formular hochladen")
    st.write(
        "Laden Sie das PDF-Formular hoch. "
        "Die KI erkennt automatisch alle Fragen und Antwortmöglichkeiten."
    )

    uploaded_file = st.file_uploader("PDF-Formular wählen", type=["pdf"])

    if uploaded_file and st.button("Formular analysieren"):
        _process_pdf(uploaded_file)


def _process_pdf(uploaded_file) -> None:
    """Verarbeitet das hochgeladene PDF und speichert die extrahierten Fragen."""
    file_bytes = uploaded_file.getvalue()

    # Schritt 1: PDF lesen (schnell, lokal)
    with st.spinner("Schritt 1/2 – PDF wird gelesen..."):
        text_content, fields_list = extract_pdf_content(file_bytes)

    st.success(f"PDF gelesen: {len(text_content)} Zeichen, {len(fields_list)} Formularfelder gefunden.")

    # Schritt 2: LLM-Analyse (dauert länger, Netzwerk-Aufruf)
    with st.spinner("Schritt 2/2 – KI analysiert das Formular... (kann bis zu 60 Sekunden dauern)"):
        try:
            client, model = get_llm_client_for_extraction()
            raw_questions = analyze_pdf_with_llm(client, model, text_content, fields_list)

            if not raw_questions:
                st.error(
                    "Die KI konnte keine Fragen erkennen. "
                    "Bitte ein anderes PDF versuchen."
                )
                return

            # Normalisierung: fehlende Felder mit leeren Standardwerten befüllen.
            # Das ist der Übergangs-Punkt zwischen den beiden Datenformaten.
            for q in raw_questions:
                q.setdefault("help_terms", {})
                q.setdefault("pdf_field_name", None)
                q.setdefault("pdf_yes_no_map", {})
                q.setdefault("pdf_mc_map", {})

            st.session_state.questions = raw_questions
            st.session_state.uploaded_pdf = file_bytes
            st.session_state.answers = {}
            st.session_state.chat_messages = []
            st.session_state.step = STEP_START
            st.rerun()

        except Exception as e:
            st.error(f"Fehler bei der KI-Analyse: {e}")
