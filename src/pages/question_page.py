"""
Fragen-Seite für die Wesentlichkeitsanalyse.

Zeigt eine dynamisch extrahierte Frage an (aus st.session_state.questions).
Zwei Spalten: Frage + Navigation links, KI-Chat-Assistent rechts.
"""

import streamlit as st

from ..llm_client import (
    get_llm_client,
    build_question_context,
    build_messages_for_api,
    get_assistant_response,
)
from ..config import STEP_UPLOAD


def _get_questions() -> list:
    """Liest die dynamischen Fragen aus dem Session State."""
    return st.session_state.get("questions", [])


def _render_single_choice(question: dict, prev_answer) -> str:
    """Rendert eine Single-Choice-Frage."""
    return st.radio(
        "Bitte wählen Sie eine Antwort:",
        question["options"],
        index=question["options"].index(prev_answer) if prev_answer in question["options"] else 0,
        key=question["id"],
    )


def _render_multi_choice(question: dict, prev_answer) -> list:
    """Rendert eine Multiple-Choice-Frage."""
    st.write("Bitte wählen Sie alle zutreffenden Optionen:")

    selected_options = []

    for opt in question["options"]:
        was_selected_before = isinstance(prev_answer, list) and opt in prev_answer

        checked = st.checkbox(
            opt,
            value=was_selected_before,
            key=f"{question['id']}_{opt}",
        )

        if checked:
            selected_options.append(opt)

    return selected_options


def _render_text(question: dict, prev_answer) -> str:
    """Rendert eine Freitext-Frage."""
    return st.text_area(
        "Ihre Antwort:",
        value=prev_answer if isinstance(prev_answer, str) else "",
        key=question["id"],
    )


def _render_help_section(question: dict):
    """Rendert den Hilfe-Bereich mit Begriffserklärungen (falls vorhanden)."""
    if "help_terms" in question and question["help_terms"]:
        with st.expander("❓ Erläuterungen zu Begriffen in dieser Frage"):
            for term, explanation in question["help_terms"].items():
                st.markdown(f"**{term}**")
                st.write(explanation)
                st.markdown("---")


def _render_chat_assistant(question: dict):
    """Rendert den KI-Chat-Assistenten in einem scrollbaren Container."""
    st.header("💬 KI-Assistent zur Unterstützung")

    st.write(
        "Sie können hier Rückfragen an einen KI-Assistenten stellen, z. B. zur aktuellen Frage, "
        "zu Begriffen oder zur Interpretation der Antwortmöglichkeiten."
    )

    chat_container = st.container(height=600)
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ihre Frage an den KI-Assistenten",
        key="chat_input",
    )

    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        question_context = build_question_context(question)

        messages_for_api = build_messages_for_api(
            question_context,
            st.session_state.project_context,
            st.session_state.chat_messages,
        )

        client, model = get_llm_client()

        with st.spinner("KI-Assistent denkt nach..."):
            reply = get_assistant_response(client, model, messages_for_api)

        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()


def render(question_index: int):
    """
    Rendert eine Fragen-Seite mit Chat nebeneinander.

    Args:
        question_index: 0-basierter Index der Frage
    """
    questions = _get_questions()

    if not questions:
        st.error("Keine Fragen geladen. Bitte zuerst ein PDF hochladen.")
        if st.button("Zum Upload"):
            st.session_state.step = STEP_UPLOAD
            st.rerun()
        return

    question = questions[question_index]

    question_col, chat_col = st.columns([1, 1], gap="large")

    # === LINKE SPALTE: Frage und Navigation ===
    with question_col:
        st.header(f"Frage {question_index + 1} von {len(questions)}")
        st.write(question["text"])

        prev_answer = st.session_state.answers.get(question["id"], None)

        if question["type"] == "single_choice":
            answer = _render_single_choice(question, prev_answer)
        elif question["type"] == "multi_choice":
            answer = _render_multi_choice(question, prev_answer)
        elif question["type"] == "text":
            answer = _render_text(question, prev_answer)
        else:
            st.error("Unbekannter Fragetyp.")
            answer = None

        st.write("")

        nav_col1, nav_col2 = st.columns(2)

        with nav_col1:
            if st.button("Zurück"):
                st.session_state.answers[question["id"]] = answer
                st.session_state.step -= 1
                st.rerun()

        with nav_col2:
            if st.button("Weiter"):
                st.session_state.answers[question["id"]] = answer
                st.session_state.step += 1
                st.rerun()

        st.write("")

        _render_help_section(question)

    # === RECHTE SPALTE: KI-Chat ===
    with chat_col:
        _render_chat_assistant(question)
