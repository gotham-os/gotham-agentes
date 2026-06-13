"""
Model factory para os Diretores GOTHAM.

Prioridade:
  1. MANIFEST_KEY_<DIRETOR> + MANIFEST_BASE_URL → usa ManifestChat (httpx direto)
  2. Groq direto como fallback

ManifestChat: GPT-5.5 via ChatGPT OAuth bloqueia o User-Agent do OpenAI Python SDK.
Solução: httpx direto com UA customizado, parsear SSE manualmente.
AgentOS HTTP server usa async (ainvoke/ainvoke_stream) — todos os 4 métodos
são sobrescritos: invoke, invoke_stream, ainvoke, ainvoke_stream.
"""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Iterator


def _make_manifest_chat(manifest_key: str, manifest_url: str):
    import httpx
    from agno.models.openai import OpenAIChat
    from agno.models.response import ModelResponse

    _key = manifest_key
    _url = manifest_url.rstrip("/")
    _headers = {
        "Authorization": f"Bearer {_key}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "gotham-agent/1.0",
    }

    def _build_body(model_id: str, formatted_messages: list, extra: dict) -> dict:
        body: dict[str, Any] = {
            "model": model_id,
            "messages": formatted_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        ep = {k: v for k, v in extra.items() if k not in ("stream", "stream_options")}
        body.update(ep)
        return body

    def _parse_sse_chunks(state: dict, line: str) -> ModelResponse | None:
        """Parse uma linha SSE e retorna ModelResponse se houver conteúdo novo."""
        line = line.strip()
        if not line or not line.startswith("data:"):
            return None
        data_str = line[5:].strip()
        if data_str == "[DONE]":
            return None
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            return None

        if "usage" in chunk and chunk["usage"]:
            u = chunk["usage"]
            state["in_tok"] = u.get("prompt_tokens", 0) or 0
            state["out_tok"] = u.get("completion_tokens", 0) or 0

        choices = chunk.get("choices", [])
        if not choices:
            return None

        delta = choices[0].get("delta", {})
        new_content = delta.get("content", "")

        for tc in delta.get("tool_calls", []):
            idx = tc.get("index", 0)
            if idx not in state["tcs"]:
                state["tcs"][idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
            if tc.get("id"):
                state["tcs"][idx]["id"] = tc["id"]
            fn = tc.get("function", {})
            if fn.get("name"):
                state["tcs"][idx]["function"]["name"] += fn["name"]
            if fn.get("arguments"):
                state["tcs"][idx]["function"]["arguments"] += fn["arguments"]

        if new_content:
            mr = ModelResponse(content=new_content)
            mr.input_tokens = state["in_tok"]
            mr.output_tokens = state["out_tok"]
            return mr
        return None

    class _ManifestChat(OpenAIChat):
        """Chama Manifest via httpx direto — contorna bloqueio de UA do OpenAI SDK."""

        def _build_tool_calls(self, tcs: dict) -> list:
            from agno.models.message import ToolCall
            return [
                ToolCall(
                    id=tc["id"],
                    type="function",
                    function={"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                )
                for tc in tcs.values()
            ]

        def _get_body(self, messages, compress_tool_results, **kwargs) -> dict:
            extra = self.get_request_params(**kwargs)
            return _build_body(
                self.id,
                self._format_all_messages(messages, compress_tool_results),
                extra,
            )

        # ── SYNC ──────────────────────────────────────────────────────────────

        def invoke(self, messages, assistant_message, response_format=None,
                   tools=None, tool_choice=None, run_response=None,
                   compress_tool_results=False):
            assistant_message.metrics.start_timer()
            state = {"in_tok": 0, "out_tok": 0, "tcs": {}}
            parts: list[str] = []
            try:
                body = self._get_body(
                    messages, compress_tool_results,
                    response_format=response_format, tools=tools,
                    tool_choice=tool_choice, run_response=run_response,
                )
                with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                    with client.stream("POST", f"{_url}/chat/completions",
                                       headers=_headers, content=json.dumps(body).encode()) as resp:
                        if resp.status_code != 200:
                            raise RuntimeError(f"Manifest {resp.status_code}: {resp.read().decode()}")
                        for line in resp.iter_lines():
                            mr = _parse_sse_chunks(state, line)
                            if mr and mr.content:
                                parts.append(mr.content)
            except Exception as e:
                from agno.exceptions import ModelProviderError
                raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e
            finally:
                assistant_message.metrics.stop_timer()

            mr = ModelResponse(content="".join(parts) or None)
            mr.input_tokens = state["in_tok"]
            mr.output_tokens = state["out_tok"]
            if state["tcs"]:
                mr.tool_calls = self._build_tool_calls(state["tcs"])
            return mr

        def invoke_stream(self, messages, assistant_message, response_format=None,
                          tools=None, tool_choice=None, run_response=None,
                          compress_tool_results=False) -> Iterator[ModelResponse]:
            assistant_message.metrics.start_timer()
            state = {"in_tok": 0, "out_tok": 0, "tcs": {}}
            try:
                body = self._get_body(
                    messages, compress_tool_results,
                    response_format=response_format, tools=tools,
                    tool_choice=tool_choice, run_response=run_response,
                )
                with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                    with client.stream("POST", f"{_url}/chat/completions",
                                       headers=_headers, content=json.dumps(body).encode()) as resp:
                        if resp.status_code != 200:
                            raise RuntimeError(f"Manifest {resp.status_code}: {resp.read().decode()}")
                        for line in resp.iter_lines():
                            mr = _parse_sse_chunks(state, line)
                            if mr:
                                yield mr

                if state["tcs"]:
                    mr = ModelResponse(content=None)
                    mr.tool_calls = self._build_tool_calls(state["tcs"])
                    mr.input_tokens = state["in_tok"]
                    mr.output_tokens = state["out_tok"]
                    yield mr

                assistant_message.metrics.stop_timer()
            except Exception as e:
                from agno.exceptions import ModelProviderError
                raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e

        # ── ASYNC ─────────────────────────────────────────────────────────────

        async def ainvoke(self, messages, assistant_message, response_format=None,
                          tools=None, tool_choice=None, run_response=None,
                          compress_tool_results=False):
            import httpx as _httpx
            assistant_message.metrics.start_timer()
            state = {"in_tok": 0, "out_tok": 0, "tcs": {}}
            parts: list[str] = []
            try:
                body = self._get_body(
                    messages, compress_tool_results,
                    response_format=response_format, tools=tools,
                    tool_choice=tool_choice, run_response=run_response,
                )
                async with _httpx.AsyncClient(timeout=_httpx.Timeout(120.0)) as client:
                    async with client.stream("POST", f"{_url}/chat/completions",
                                              headers=_headers, content=json.dumps(body).encode()) as resp:
                        if resp.status_code != 200:
                            raise RuntimeError(f"Manifest {resp.status_code}: {await resp.aread()}")
                        async for line in resp.aiter_lines():
                            mr = _parse_sse_chunks(state, line)
                            if mr and mr.content:
                                parts.append(mr.content)
            except Exception as e:
                from agno.exceptions import ModelProviderError
                raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e
            finally:
                assistant_message.metrics.stop_timer()

            mr = ModelResponse(content="".join(parts) or None)
            mr.input_tokens = state["in_tok"]
            mr.output_tokens = state["out_tok"]
            if state["tcs"]:
                mr.tool_calls = self._build_tool_calls(state["tcs"])
            return mr

        async def ainvoke_stream(self, messages, assistant_message, response_format=None,
                                  tools=None, tool_choice=None, run_response=None,
                                  compress_tool_results=False) -> AsyncIterator[ModelResponse]:
            import httpx as _httpx
            assistant_message.metrics.start_timer()
            state = {"in_tok": 0, "out_tok": 0, "tcs": {}}
            try:
                body = self._get_body(
                    messages, compress_tool_results,
                    response_format=response_format, tools=tools,
                    tool_choice=tool_choice, run_response=run_response,
                )
                async with _httpx.AsyncClient(timeout=_httpx.Timeout(120.0)) as client:
                    async with client.stream("POST", f"{_url}/chat/completions",
                                              headers=_headers, content=json.dumps(body).encode()) as resp:
                        if resp.status_code != 200:
                            raise RuntimeError(f"Manifest {resp.status_code}: {await resp.aread()}")
                        async for line in resp.aiter_lines():
                            mr = _parse_sse_chunks(state, line)
                            if mr:
                                yield mr

                if state["tcs"]:
                    mr = ModelResponse(content=None)
                    mr.tool_calls = self._build_tool_calls(state["tcs"])
                    mr.input_tokens = state["in_tok"]
                    mr.output_tokens = state["out_tok"]
                    yield mr

                assistant_message.metrics.stop_timer()
            except Exception as e:
                from agno.exceptions import ModelProviderError
                raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e

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
