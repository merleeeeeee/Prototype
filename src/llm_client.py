"""
LLM-Client für den KI-Chat-Assistenten.

Stellt die Verbindung zum Uni-LLM her und bietet Funktionen
für die Chat-Kommunikation auf den Fragen-Seiten.
"""

import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from .config import DEFAULT_CHAT_MODEL, CHAT_SYSTEM_PROMPT, LLM_TEMPERATURE_CHAT, LLM_MAX_TOKENS

HIDDEN_CONTEXT_PATH = "context/hidden_context.txt"


def load_hidden_context() -> str:
    """Lädt versteckten Kontext aus einer Datei, falls vorhanden."""
    if os.path.exists(HIDDEN_CONTEXT_PATH):
        with open(HIDDEN_CONTEXT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


@st.cache_resource
def get_llm_client():
    """
    Erstellt und cached einen OpenAI-kompatiblen Client für den Chat-Assistenten.

    Returns:
        Tuple[OpenAI, str]: (client, model_name)
    """
    load_dotenv()

    base_url = os.getenv("UNI_LLM_BASE_URL")
    api_key = os.getenv("UNI_LLM_API_KEY")
    chat_model = os.getenv("UNI_LLM_CHAT_MODEL", DEFAULT_CHAT_MODEL)

    if not base_url or not api_key:
        raise RuntimeError(
            "Bitte UNI_LLM_BASE_URL und UNI_LLM_API_KEY in der .env setzen."
        )

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    return client, chat_model


def build_question_context(question: dict) -> str:
    """
    Baut den Kontext-String für die aktuelle Frage auf.

    Funktioniert auch bei dynamisch extrahierten Fragen ohne help_terms.

    Args:
        question: Das Frage-Dictionary

    Returns:
        Formatierter Kontext-String
    """
    parts = [f"Fragetext: {question['text']}"]

    if question["type"] in ("single_choice", "multi_choice") and "options" in question:
        options_str = "; ".join(question["options"])
        parts.append(f"Antwortoptionen: {options_str}")

    if "help_terms" in question and question["help_terms"]:
        help_str = "; ".join(
            f"{term}: {expl}" for term, expl in question["help_terms"].items()
        )
        parts.append(f"Erläuterungen: {help_str}")

    return " | ".join(parts)


def build_messages_for_api(
    question_context: str,
    project_context: str,
    chat_messages: list,
) -> list:
    """
    Baut die Nachrichten-Liste für den API-Aufruf auf.

    Args:
        question_context: Kontext der aktuellen Frage
        project_context: Projektkontext des Nutzers
        chat_messages: Bisheriger Chat-Verlauf

    Returns:
        Liste der Nachrichten für die API
    """
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "system", "content": f"Aktuelle Frage im Fragebogen: {question_context}"},
    ]

    hidden_context = load_hidden_context()
    if hidden_context:
        messages.append({
            "role": "system",
            "content": f"Zusätzlicher Hintergrundkontext:\n{hidden_context}",
        })

    # Handbuch-Text aus Session State (hochgeladen vom Nutzer)
    # Wird auf MAX_HANDBOOK_TEXT_LENGTH gekürzt, um den Kontext nicht zu überlasten
    handbook_text: str = st.session_state.get("handbook_text", "")
    if handbook_text.strip():
        from .config import MAX_HANDBOOK_TEXT_LENGTH
        truncated = handbook_text[:MAX_HANDBOOK_TEXT_LENGTH]
        messages.append({
            "role": "system",
            "content": (
                "Handbuch-Text (Quelle für Zitate und Definitionen):\n"
                "Wenn du nach Definitionen oder Erklärungen gefragt wirst, "
                "zitiere wortgetreu aus diesem Text und weise auf die Herkunft hin.\n"
                f"---\n{truncated}\n---"
            ),
        })

    if project_context.strip():
        messages.append({
            "role": "system",
            "content": f"Projektkontext des Nutzers (zur Einordnung der Antworten): {project_context}",
        })

    messages.extend(chat_messages)
    return messages


def get_assistant_response(client: OpenAI, model: str, messages: list) -> str:
    """
    Ruft das LLM auf und gibt die Antwort zurück.

    Args:
        client: OpenAI-Client
        model: Modellname
        messages: Nachrichten-Liste für die API

    Returns:
        Antwort des Assistenten als String
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=LLM_TEMPERATURE_CHAT,
            max_tokens=LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Beim Aufruf des Modells ist ein Fehler aufgetreten:\n\n`{e}`"
