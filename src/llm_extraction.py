"""
LLM-Service für die PDF-Extraktion.

Kommuniziert mit dem Uni-LLM, um strukturierte Fragen aus PDF-Inhalt zu extrahieren.
"""

import json
import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from .config import DEFAULT_CHAT_MODEL, LLM_TEMPERATURE_EXTRACT, LLM_EXTRACTION_SYSTEM_PROMPT
from .config import MAX_PDF_TEXT_LENGTH, MAX_FIELDS_TEXT_LENGTH

# Timeout in Sekunden für den LLM-API-Call
LLM_TIMEOUT_SECONDS = 120


@st.cache_resource
def get_llm_client_for_extraction() -> tuple[OpenAI, str]:
    """
    Erstellt und cached einen OpenAI-kompatiblen Client für das Uni-LLM (Extraktion).

    Lädt die Konfiguration aus Umgebungsvariablen:
    - UNI_LLM_BASE_URL: Die Basis-URL der LLM-API
    - UNI_LLM_API_KEY: Der API-Schlüssel
    - UNI_LLM_CHAT_MODEL: Das zu verwendende Modell (optional)

    Returns:
        Tuple aus (OpenAI-Client, Modellname).

    Raises:
        RuntimeError: Wenn erforderliche Umgebungsvariablen fehlen.
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
        timeout=LLM_TIMEOUT_SECONDS,
    )
    return client, chat_model


def analyze_pdf_with_llm(
    client: OpenAI,
    model: str,
    text_content: str,
    fields_list: list[str],
) -> list[dict[str, Any]]:
    """
    Analysiert PDF-Inhalt mit dem LLM und extrahiert strukturierte Fragen.

    Args:
        client: Der OpenAI-kompatible API-Client.
        model: Der Name des zu verwendenden LLM-Modells.
        text_content: Der extrahierte Textinhalt des PDFs.
        fields_list: Liste der gefundenen Formularfelder.

    Returns:
        Liste von Frage-Dictionaries mit id, text, type, options,
        pdf_field_name, pdf_yes_no_map, pdf_mc_map.
    """
    if not client:
        raise ValueError("LLM-Client ist nicht initialisiert.")

    truncated_text = text_content[:MAX_PDF_TEXT_LENGTH]
    truncated_fields = str(fields_list)[:MAX_FIELDS_TEXT_LENGTH]

    user_prompt = f"""
Hier ist der Text des PDFs:
---
{truncated_text} (gekürzt falls zu lang)
---

Hier ist die Liste der gefundenen Formularfelder im PDF (Internal Names):
---
{truncated_fields}
---

Generiere jetzt das JSON Array.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LLM_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=LLM_TEMPERATURE_EXTRACT,
        timeout=LLM_TIMEOUT_SECONDS,
    )

    content = response.choices[0].message.content

    # Markdown Code-Blöcke entfernen, falls das LLM welche sendet
    content = content.replace("```json", "").replace("```", "").strip()

    return json.loads(content)
