"""
Model factory para os Diretores GOTHAM.

Prioridade:
  1. MANIFEST_KEY_<DIRETOR> + MANIFEST_BASE_URL → usa ManifestChat (httpx direto)
  2. Groq direto como fallback

ManifestChat: GPT-5.5 via ChatGPT OAuth só aceita stream=True e bloqueia
o User-Agent do OpenAI Python SDK. Solução: chamar a API diretamente via
httpx (sem o SDK), parsear SSE manualmente e retornar ModelResponse.
"""
from __future__ import annotations

import json
import os
from typing import Any


def _make_manifest_chat(manifest_key: str, manifest_url: str):
    import httpx
    from agno.models.openai import OpenAIChat
    from agno.models.response import ModelResponse

    class _ManifestChat(OpenAIChat):
        """Chama Manifest via httpx direto para contornar bloqueio de UA do SDK."""

        _manifest_key: str = manifest_key
        _manifest_url: str = manifest_url.rstrip("/")

        def invoke(self, messages, assistant_message, response_format=None,
                   tools=None, tool_choice=None, run_response=None,
                   compress_tool_results=False):
            assistant_message.metrics.start_timer()

            content_parts: list[str] = []
            tool_calls_map: dict[int, dict] = {}
            input_tokens = 0
            output_tokens = 0

            try:
                body: dict[str, Any] = {
                    "model": self.id,
                    "messages": self._format_all_messages(messages, compress_tool_results),
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }

                # Parâmetros extras (temperature, tools, etc.)
                extra = self.get_request_params(
                    response_format=response_format,
                    tools=tools,
                    tool_choice=tool_choice,
                    run_response=run_response,
                )
                # Remove stream se vier nos params extras (evita conflito)
                extra.pop("stream", None)
                extra.pop("stream_options", None)
                body.update(extra)

                with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                    with client.stream(
                        "POST",
                        f"{self._manifest_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._manifest_key}",
                            "Content-Type": "application/json",
                            "Accept": "*/*",
                            "User-Agent": "gotham-agent/1.0",
                        },
                        content=json.dumps(body).encode(),
                        timeout=httpx.Timeout(120.0),
                    ) as resp:
                        if resp.status_code != 200:
                            body_text = resp.read().decode()
                            raise RuntimeError(
                                f"Manifest HTTP {resp.status_code}: {body_text}"
                            )

                        for raw_line in resp.iter_lines():
                            line = raw_line.strip()
                            if not line or not line.startswith("data:"):
                                continue
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            # Usage (pode vir em chunk sem choices)
                            if "usage" in chunk and chunk["usage"]:
                                u = chunk["usage"]
                                input_tokens = u.get("prompt_tokens", 0) or 0
                                output_tokens = u.get("completion_tokens", 0) or 0

                            choices = chunk.get("choices", [])
                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})

                            if delta.get("content"):
                                content_parts.append(delta["content"])

                            for tc in delta.get("tool_calls", []):
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {
                                        "id": tc.get("id") or "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    }
                                if tc.get("id"):
                                    tool_calls_map[idx]["id"] = tc["id"]
                                fn = tc.get("function", {})
                                if fn.get("name"):
                                    tool_calls_map[idx]["function"]["name"] += fn["name"]
                                if fn.get("arguments"):
                                    tool_calls_map[idx]["function"]["arguments"] += fn["arguments"]

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
                from agno.models.message import ToolCall
                mr.tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        type="function",
                        function={
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    )
                    for tc in tool_calls_map.values()
                ]

            return mr

    return _ManifestChat(
        id="auto",
        api_key=manifest_key,
        base_url=manifest_url,
    )


def get_model(director: str, groq_model: str):
    manifest_key = os.getenv(f"MANIFEST_KEY_{director.upper()}")
    manifest_url = os.getenv("MANIFEST_BASE_URL", "https://roteador.bmilimitada.com/v1")

    if manifest_key:
        return _make_manifest_chat(manifest_key, manifest_url)

    from agno.models.groq import Groq
    return Groq(id=groq_model)
