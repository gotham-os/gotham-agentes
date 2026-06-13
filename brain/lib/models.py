"""
Model factory para os Diretores GOTHAM.

Prioridade:
  1. MANIFEST_KEY_<DIRETOR> + MANIFEST_BASE_URL → usa Manifest Router (roteador.bmilimitada.com)
  2. Groq direto como fallback

Quando Manifest está ativo:
  - model="auto" → Manifest decide por complexidade (routing rules do dashboard)
  - Troca de LLM = só no dashboard, sem redeploy
  - Fallback chain configurado por agente no dashboard
"""
from __future__ import annotations

import os


def get_model(director: str, groq_model: str):
    """
    Retorna o modelo correto para o Diretor.

    Args:
        director: "alfred" | "ras" | "selina" | "bruce"
        groq_model: model ID do Groq usado como fallback direto
    """
    manifest_key = os.getenv(f"MANIFEST_KEY_{director.upper()}")
    manifest_url = os.getenv("MANIFEST_BASE_URL", "https://roteador.bmilimitada.com/v1")

    if manifest_key:
        from agno.models.openai import OpenAIChat
        return OpenAIChat(
            id="auto",
            api_key=manifest_key,
            base_url=manifest_url,
            stream=True,
        )

    # Fallback: Groq direto
    from agno.models.groq import Groq
    return Groq(id=groq_model)
