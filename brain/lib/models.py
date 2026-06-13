"""
Model factory para os Diretores GOTHAM.

Prioridade:
  1. MANIFEST_KEY_<DIRETOR> + MANIFEST_BASE_URL → usa ManifestChat (stream=True forçado)
  2. Groq direto como fallback

ManifestChat: GPT-5.5 via OAuth só aceita stream=True.
Subclasse que intercepta invoke() e usa invoke_stream() internamente,
agregando os deltas antes de retornar o ModelResponse completo.
"""
from __future__ import annotations

import os


class ManifestChat:
    """Lazy wrapper — instanciado apenas se MANIFEST_KEY estiver presente."""
    pass


def _make_manifest_chat(manifest_key: str, manifest_url: str):
    from agno.models.openai import OpenAIChat
    from agno.models.response import ModelResponse

    class _ManifestChat(OpenAIChat):
        """Force stream=True para Manifest Router (GPT-5.5 subscription OAuth)."""

        def invoke(self, messages, assistant_message, response_format=None,
                   tools=None, tool_choice=None, run_response=None,
                   compress_tool_results=False):
            assistant_message.metrics.start_timer()

            content_parts: list[str] = []
            tool_calls_map: dict[int, dict] = {}
            input_tokens = 0
            output_tokens = 0

            try:
                stream = self.get_client().chat.completions.create(
                    model=self.id,
                    messages=self._format_all_messages(messages, compress_tool_results),
                    stream=True,
                    stream_options={"include_usage": True},
                    **self.get_request_params(
                        response_format=response_format,
                        tools=tools,
                        tool_choice=tool_choice,
                        run_response=run_response,
                    ),
                )

                for chunk in stream:
                    if not chunk.choices:
                        if hasattr(chunk, "usage") and chunk.usage:
                            input_tokens = chunk.usage.prompt_tokens or 0
                            output_tokens = chunk.usage.completion_tokens or 0
                        continue

                    delta = chunk.choices[0].delta

                    if delta.content:
                        content_parts.append(delta.content)

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_map:
                                tool_calls_map[idx] = {
                                    "id": tc.id or "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            if tc.id:
                                tool_calls_map[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_map[idx]["function"]["name"] += tc.function.name
                                if tc.function.arguments:
                                    tool_calls_map[idx]["function"]["arguments"] += tc.function.arguments

                    if hasattr(chunk, "usage") and chunk.usage:
                        input_tokens = chunk.usage.prompt_tokens or 0
                        output_tokens = chunk.usage.completion_tokens or 0

            except Exception as e:
                from agno.exceptions import ModelProviderError
                raise ModelProviderError(
                    message=str(e), model_name=self.name, model_id=self.id
                ) from e
            finally:
                assistant_message.metrics.stop_timer()

            content = "".join(content_parts) if content_parts else None

            mr = ModelResponse(content=content)
            mr.input_tokens = input_tokens
            mr.output_tokens = output_tokens

            if tool_calls_map:
                import json
                from agno.models.message import ToolCall
                mr.tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        type="function",
                        function={"name": tc["function"]["name"],
                                  "arguments": tc["function"]["arguments"]},
                    )
                    for tc in tool_calls_map.values()
                ]

            return mr

    import httpx

    def _override_ua(request: httpx.Request) -> None:
        request.headers["user-agent"] = "gotham-agent/1.0"
        request.headers["accept"] = "*/*"

    http_client = httpx.Client(
        event_hooks={"request": [_override_ua]},
        timeout=httpx.Timeout(120.0),
    )

    return _ManifestChat(
        id="auto",
        api_key=manifest_key,
        base_url=manifest_url,
        http_client=http_client,
    )


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
        return _make_manifest_chat(manifest_key, manifest_url)

    from agno.models.groq import Groq
    return Groq(id=groq_model)
