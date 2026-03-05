"""
Upload-Seite: Formular-PDF und optionales Handbuch hochladen.

Ablauf:
1. Formular-PDF → pypdf extrahiert Text + Felder
2. LLM extrahiert strukturierte Fragen aus dem Formular
3. Falls Handbuch hochgeladen: Text wird extrahiert und
   LLM reichert jede Frage mit relevanten Definitionen an (help_terms).
   Der Handbuch-Text wird außerdem in session_state gespeichert,
   damit der Chat-Assistent daraus zitieren kann.
"""

import streamlit as st

from ..pdf_extractor import extract_pdf_content
from ..llm_extraction import get_llm_client_for_extraction, analyze_pdf_with_llm
from ..handbook_service import extract_handbook_text, enrich_questions_with_definitions
from ..config import STEP_START


def render():
    """Rendert die Upload-Seite."""
    st.title("📄 Formular hochladen")
    st.write(
        "Laden Sie das PDF-Formular hoch. "
        "Die KI erkennt automatisch alle Fragen und Antwortmöglichkeiten."
    )

    # ── Formular-Upload ────────────────────────────────────────────────────
    st.subheader("pdf wählen")
    form_file = st.file_uploader("PDF-Formular wählen", type=["pdf"])

    st.markdown("---")

    # ── Handbuch-Upload (optional) ─────────────────────────────────────────
    st.subheader("Handbuch wählen")
    st.write(
        "Optional: Laden Sie ein Handbuch hoch (PDF, Word oder TXT). "
        "Die KI liest daraus automatisch die relevanten Definitionen für jede Frage aus "
        "und zeigt sie direkt unter der jeweiligen Frage an. "
        "Der Chat-Assistent kann ebenfalls aus dem Handbuch zitieren."
    )
    handbook_file = st.file_uploader(
        "Handbuch wählen (optional)",
        type=["pdf", "docx", "doc", "txt"],
        key="handbook_uploader",
    )

    st.markdown("---")

    if form_file and st.button("Formular analysieren", type="primary"):
        _process(form_file, handbook_file)


def _process(form_file, handbook_file) -> None:
    """Verarbeitet Formular (+ optionales Handbuch) und speichert Ergebnisse."""

    # ── Schritt 1: Formular-PDF lesen ──────────────────────────────────────
    with st.spinner("Schritt 1/3 – Formular-PDF wird gelesen..."):
        form_bytes = form_file.getvalue()
        text_content, fields_list = extract_pdf_content(form_bytes)

    st.success(
        f"Formular gelesen: {len(text_content)} Zeichen, "
        f"{len(fields_list)} Formularfelder gefunden."
    )

    # ── Schritt 2: LLM extrahiert Fragen ──────────────────────────────────
    try:
        client, model = get_llm_client_for_extraction()
    except Exception as e:
        st.error(f"LLM-Client konnte nicht initialisiert werden: {e}")
        return

    # Schnell-Test: Prüft ob das Modell gerade erreichbar ist (max. 10s)
    with st.spinner(f"Schritt 2/3 – Verbindung zu **{model}** wird geprüft..."):
        try:
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=1,
                timeout=10,
            )
        except Exception:
            st.error(
                f"Das Modell **{model}** antwortet nicht. "
                "Bitte `UNI_LLM_CHAT_MODEL` in der `.env` auf ein verfügbares Modell setzen "
                "(z.B. `Llama-3.3-70B` oder `mistral-small`) und die App neu starten."
            )
            return

    st.write(f"**Fragen werden aus dem Formular extrahiert...**")
    extract_progress = st.progress(0)
    extract_status   = st.empty()
    extract_status.caption(
        f"Sende {len(text_content)} Zeichen Text und "
        f"{len(fields_list)} Formularfelder an {model}..."
    )

    try:
        raw_questions = analyze_pdf_with_llm(client, model, text_content, fields_list)
    except Exception as e:
        extract_progress.progress(1.0)
        extract_status.empty()
        st.error(f"Fehler bei der Formular-Analyse: {e}")
        return

    extract_progress.progress(1.0)
    extract_status.empty()

    if not raw_questions:
        st.error("Die KI konnte keine Fragen erkennen. Bitte ein anderes PDF versuchen.")
        return

    # Normalisierung
    for q in raw_questions:
        q.setdefault("help_terms", {})
        q.setdefault("pdf_field_name", None)
        q.setdefault("pdf_yes_no_map", {})
        q.setdefault("pdf_mc_map", {})

    st.success(f"Fragen extrahiert: {len(raw_questions)} Fragen erkannt.")

    # ── Schritt 3: Handbuch (optional) ────────────────────────────────────
    handbook_text = ""
    if handbook_file:
        try:
            # 3a: Handbuch-Text extrahieren
            with st.spinner("Schritt 3/3 – Handbuch wird gelesen..."):
                handbook_text = extract_handbook_text(
                    handbook_file.getvalue(), handbook_file.name
                )
            st.success(f"Handbuch gelesen: {len(handbook_text)} Zeichen.")

            # 3b: Pro Frage eine LLM-Analyse — mit Fortschrittsanzeige
            st.write("**Definitionen werden aus dem Handbuch extrahiert...**")
            progress_bar  = st.progress(0)
            status_text   = st.empty()
            total         = len(raw_questions)

            def _progress(current: int, total: int, question_text: str):
                pct = current / total
                progress_bar.progress(pct)
                short = question_text[:60] + "…" if len(question_text) > 60 else question_text
                status_text.caption(f"Frage {current + 1}/{total}: {short}")

            raw_questions = enrich_questions_with_definitions(
                client, model, handbook_text, raw_questions,
                progress_callback=_progress,
            )

            progress_bar.progress(1.0)
            status_text.empty()

            defined = sum(1 for q in raw_questions if q.get("help_terms"))
            st.success(
                f"Handbuch ausgewertet: Definitionen für {defined} von {total} Fragen gefunden."
            )
        except Exception as e:
            st.warning(
                f"Handbuch konnte nicht vollständig ausgewertet werden: {e}\n\n"
                "Die Fragen wurden trotzdem extrahiert."
            )
    else:
        st.info("Kein Handbuch hochgeladen – Schritt 3 wird übersprungen.")

    # ── Session State befüllen und weiterleiten ────────────────────────────
    st.session_state.questions     = raw_questions
    st.session_state.handbook_text = handbook_text   # für Chat-Assistent
    st.session_state.uploaded_pdf  = form_bytes
    st.session_state.answers       = {}
    st.session_state.chat_messages = []
    st.session_state.step          = STEP_START
    st.rerun()
