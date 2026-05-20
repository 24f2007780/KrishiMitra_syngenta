"""Gemini replies with persona + optional RAG context (same client style as voice_pipeline)."""

from __future__ import annotations

import logging

from google import genai

logger = logging.getLogger(__name__)

TEXT_CHANNEL_ADDENDUM = """
# Channel
You are replying on WhatsApp (text). Keep answers concise: prefer short paragraphs or bullet points.
Do not use markdown headings; plain text only.
Mirror the user's language per your language policy above.
"""


class GeminiSupportBot:
    def __init__(self, api_key: str, system_instruction: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._system = system_instruction.strip() + "\n\n" + TEXT_CHANNEL_ADDENDUM.strip()
        self._model = model

    def reply(self, user_message: str, rag_context: str) -> str:
        context_block = ""
        if rag_context.strip():
            context_block = (
                "Use ONLY the following knowledge base excerpts when stating org-specific facts. "
                "If they do not contain the answer, say you are not sure and offer a human agent.\n\n"
                f"---\n{rag_context}\n---\n\n"
            )
        user_part = context_block + f"Customer message:\n{user_message.strip()}"

        response = self._client.models.generate_content(
            model=self._model,
            contents=[{"role": "user", "parts": [{"text": user_part}]}],
            config={"system_instruction": self._system},
        )
        text = (response.text or "").strip()
        if not text:
            return (
                "Thanks for your message. I could not generate a reply just now. "
                "Please try again in a moment or ask for a human agent."
            )
        return text


def from_env(system_instruction: str) -> GeminiSupportBot:
    from whatsapp_bot.config import gemini_api_key, llm_model

    return GeminiSupportBot(gemini_api_key(), system_instruction, llm_model())
