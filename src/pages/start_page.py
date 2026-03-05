"""
Startseite der Wesentlichkeitsanalyse.

Zeigt alle erkannten Fragen in einer einheitlichen Ansicht:
- Drag-and-drop zum Umsortieren (oben)
- Aufklappbare Editoren direkt darunter (in gleicher Reihenfolge)
- Löschen und neue Fragen hinzufügen
"""

import uuid
import streamlit as st
from streamlit_sortables import sort_items

from ..config import STEP_UPLOAD

QUESTION_TYPE_LABELS = {
    "single_choice": "Einfachauswahl (eine Option)",
    "multi_choice":  "Mehrfachauswahl (mehrere Optionen)",
    "text":          "Freitext",
}
QUESTION_TYPES = list(QUESTION_TYPE_LABELS.keys())


def _save_question(i: int, new_text: str, new_type: str, new_options: list[str]):
    st.session_state.questions[i]["text"] = new_text
    st.session_state.questions[i]["type"] = new_type
    if new_type in ("single_choice", "multi_choice"):
        st.session_state.questions[i]["options"] = new_options
    else:
        st.session_state.questions[i].pop("options", None)


def _delete_question(i: int):
    st.session_state.questions.pop(i)


def _add_question():
    new_q = {
        "id":             f"manual_{uuid.uuid4().hex[:8]}",
        "text":           "Neue Frage",
        "type":           "single_choice",
        "options":        ["Ja", "Nein"],
        "help_terms":     {},
        "pdf_field_name": None,
        "pdf_yes_no_map": {},
        "pdf_mc_map":     {},
    }
    st.session_state.questions.append(new_q)


def _render_question_editor(i: int, q: dict):
    """Bearbeitungsformular für eine einzelne Frage."""
    q_id = q["id"]

    new_text = st.text_area(
        "Fragetext:",
        value=q.get("text", ""),
        key=f"text_{i}_{q_id}",
        height=80,
    )

    current_type = q.get("type", "text")
    type_idx = QUESTION_TYPES.index(current_type) if current_type in QUESTION_TYPES else 0
    new_type = st.selectbox(
        "Fragetyp:",
        options=QUESTION_TYPES,
        index=type_idx,
        format_func=lambda x: QUESTION_TYPE_LABELS[x],
        key=f"type_{i}_{q_id}",
    )

    new_options = q.get("options", [])
    if new_type in ("single_choice", "multi_choice"):
        options_str = st.text_area(
            "Antwortoptionen (getrennt durch **---**):",
            value="\n---\n".join(q.get("options", [])),
            key=f"options_{i}_{q_id}",
            height=140,
        )
        new_options = [o.strip() for o in options_str.split("---") if o.strip()]

    btn_col1, btn_col2 = st.columns([2, 1])
    with btn_col1:
        if st.button("💾 Speichern", key=f"save_{i}_{q_id}"):
            _save_question(i, new_text, new_type, new_options)
            st.rerun()
    with btn_col2:
        if st.button("🗑️ Frage löschen", key=f"delete_{i}_{q_id}", type="secondary"):
            _delete_question(i)
            st.rerun()


def render():
    st.title("Wesentlichkeitsanalyse")
    st.subheader("Erkannte Fragen prüfen und anpassen")

    questions = st.session_state.get("questions", [])

    if not questions:
        st.warning("Keine Fragen geladen. Bitte zuerst ein PDF hochladen.")
        if st.button("⬅️ Zum Upload"):
            st.session_state.step = STEP_UPLOAD
            st.rerun()
        return

    st.markdown(
        f"**{len(questions)} Fragen** erkannt. "
        "Reihenfolge per Drag & Drop anpassen — Frage aufklappen zum Bearbeiten."
    )

    # ── Drag-and-drop Reihenfolge ──────────────────────────────────────────
    sort_labels = [
        f"Frage {i + 1}:  {q.get('text', '')[:70]}{'…' if len(q.get('text', '')) > 70 else ''}"
        for i, q in enumerate(questions)
    ]

    _SORTABLE_STYLE = """
    .sortable-item, .sortable-item:hover {
        background-color: #262730;
        color: #fafafa;
        text-align: left;
        padding-left: 12px;
        border-radius: 4px;
    }
    """

    sorted_labels = sort_items(sort_labels, direction="vertical", custom_style=_SORTABLE_STYLE)

    if sorted_labels != sort_labels:
        new_order = [
            int(label.split(":")[0].replace("Frage", "").strip()) - 1
            for label in sorted_labels
        ]
        st.session_state.questions = [questions[i] for i in new_order]
        st.rerun()

    # ── Aufklappbare Editoren (gleiche Reihenfolge wie oben) ───────────────
    st.markdown("---")
    for i, q in enumerate(questions):
        label = (
            f"Frage {i + 1}: {q.get('text', '')[:70]}"
            f"{'…' if len(q.get('text', '')) > 70 else ''}"
        )
        with st.expander(label, expanded=False):
            _render_question_editor(i, q)

    # ── Neue Frage hinzufügen ──────────────────────────────────────────────
    st.markdown("---")
    if st.button("➕ Neue Frage manuell hinzufügen"):
        _add_question()
        st.rerun()

    # ── Navigation ────────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Zurück zum Upload"):
            st.session_state.step = STEP_UPLOAD
            st.rerun()
    with col2:
        if st.button("Weiter zur Analyse ▶️", type="primary"):
            st.session_state.step = 0
            st.rerun()
