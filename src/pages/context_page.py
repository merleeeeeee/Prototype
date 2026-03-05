"""
Projektkontext-Seite für die Wesentlichkeitsanalyse.
"""

import streamlit as st


def render():
    """Rendert die Projektkontext-Seite."""
    st.title("Projektkontext für die Wesentlichkeitsanalyse")

    st.write(
        """
        Bevor Sie mit den Fragen beginnen, können Sie hier kurz den Kontext Ihres Projekts
        beschreiben (z.B. Art des Projekts, Organisation, relevante Prozesse).
        Der KI-Assistent nutzt diese Informationen, um Antworten besser einordnen zu können.
        """
    )

    context_text = st.text_area(
        "Projektkontext (optional):",
        value=st.session_state.project_context,
        height=200,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Zurück zur Startseite"):
            st.session_state.project_context = context_text
            st.session_state.step = -1
            st.rerun()

    with col2:
        if st.button("Weiter zur ersten Frage"):
            st.session_state.project_context = context_text
            st.session_state.step = 1
            st.rerun()
