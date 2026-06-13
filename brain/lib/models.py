"""
Model factory para os Diretores GOTHAM.

Prioridade:
  1. MANIFEST_KEY_<DIRETOR> + MANIFEST_BASE_URL → usa ManifestChat (httpx direto)
  2. Groq direto como fallback

ManifestChat: GPT-5.5 via ChatGPT OAuth bloqueia o User-Agent do OpenAI Python SDK.
Solução: chamar a API diretamente via httpx, parsear SSE manualmente.
Tanto invoke() (non-stream) quanto invoke_stream() (SSE via AgentOS HTTP) são
sobrescritos — o AgentOS usa invoke_stream() mesmo com stream=false na request.
"""
from __future__ import annotations

import json
import os
from typing import Any, Iterator


def _make_manifest_chat(manifest_key: str, manifest_url: str):
    import httpx
    from agno.models.openai import OpenAIChat
    from agno.models.response import ModelResponse

    _key = manifest_key
    _url = manifest_url.rstrip("/")

    def _stream_manifest(
        model_id: str,
        formatted_messages: list,
        extra_params: dict,
    ) -> Iterator[tuple[list[str], dict, int, int]]:
        """Faz a chamada SSE ao Manifest e yield (content_parts, tool_calls_map, in_tok, out_tok)."""
        body: dict[str, Any] = {
            "model": model_id,
            "messages": formatted_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        ep = extra_params.copy()
        ep.pop("stream", None)
        ep.pop("stream_options", None)
        body.update(ep)

        content_parts: list[str] = []
        tool_calls_map: dict[int, dict] = {}
        input_tokens = 0
        output_tokens = 0

        with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
            with client.stream(
                "POST",
                f"{_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {_key}",
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "User-Agent": "gotham-agent/1.0",
                },
                content=json.dumps(body).encode(),
                timeout=httpx.Timeout(120.0),
            ) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Manifest HTTP {resp.status_code}: {resp.read().decode()}"
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

                    # yield parcial para invoke_stream poder fazer streaming real
                    if delta.get("content"):
                        yield (content_parts[:], tool_calls_map.copy(), input_tokens, output_tokens)

        # yield final com dados completos
        yield (content_parts, tool_calls_map, input_tokens, output_tokens)

    class _ManifestChat(OpenAIChat):
        """Chama Manifest via httpx direto — contorna bloqueio de UA do OpenAI SDK."""

        def _build_tool_calls(self, tool_calls_map: dict) -> list:
            from agno.models.message import ToolCall
            return [
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

        def invoke(self, messages, assistant_message, response_format=None,
                   tools=None, tool_choice=None, run_response=None,
                   compress_tool_results=False):
            assistant_message.metrics.start_timer()
            try:
                extra = self.get_request_params(
                    response_format=response_format,
                    tools=tools,
                    tool_choice=tool_choice,
                    run_response=run_response,
                )
                formatted = self._format_all_messages(messages, compress_tool_results)

                content_parts, tool_calls_map, input_tokens, output_tokens = ([], {}, 0, 0)
                for content_parts, tool_calls_map, input_tokens, output_tokens in _stream_manifest(
                    self.id, formatted, extra
                ):
                    pass  # consumir até o final

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
                mr.tool_calls = self._build_tool_calls(tool_calls_map)
            return mr

        def invoke_stream(self, messages, assistant_message, response_format=None,
                          tools=None, tool_choice=None, run_response=None,
                          compress_tool_results=False):
            try:
                assistant_message.metrics.start_timer()
                extra = self.get_request_params(
                    response_format=response_format,
                    tools=tools,
                    tool_choice=tool_choice,
                    run_response=run_response,
                )
                formatted = self._format_all_messages(messages, compress_tool_results)

                prev_len = 0
                final_tool_calls_map: dict = {}
                final_in = 0
                final_out = 0

                for content_parts, tool_calls_map, in_tok, out_tok in _stream_manifest(
                    self.id, formatted, extra
                ):
                    final_tool_calls_map = tool_calls_map
                    final_in = in_tok
                    final_out = out_tok

                    # Emitir apenas o delta novo
                    joined = "".join(content_parts)
                    new_text = joined[prev_len:]
                    prev_len = len(joined)

                    if new_text:
                        mr = ModelResponse(content=new_text)
                        mr.input_tokens = in_tok
                        mr.output_tokens = out_tok
                        yield mr

                # Emitir tool calls no final se houver
                if final_tool_calls_map:
                    mr = ModelResponse(content=None)
                    mr.tool_calls = self._build_tool_calls(final_tool_calls_map)
                    mr.input_tokens = final_in
                    mr.output_tokens = final_out
                    yield mr

                assistant_message.metrics.stop_timer()

            except Exception as e:
                from agno.exceptions import ModelProviderError
                raise ModelProviderError(
                    message=str(e), model_name=self.name, model_id=self.id
                ) from e

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
