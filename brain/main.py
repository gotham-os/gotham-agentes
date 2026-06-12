"""
GOTHAM Brain — AgentOS server

Expõe todos os agentes via FastAPI (AgentOS Agno v2).
Cada agente recebe sua rota REST + WebSocket para streaming.

Endpoints gerados automaticamente pelo AgentOS:
  GET  /v1/playground/agents            → lista agentes
  POST /v1/playground/agents/{id}/runs  → chat / run
  GET  /v1/playground/agents/{id}/sessions → histórico

Para rodar localmente:
  uvicorn main:app --reload --port 8000

Para rodar via Docker:
  docker compose up brain
"""
import os
from dotenv import load_dotenv

load_dotenv()

from agno.agent import Agent
from agno.app.fastapi.app import FastAPIApp
from agents import alfred_agent, minerador_agent, copywriter_agent, pesquisador_agent

app = FastAPIApp(
    agents=[
        alfred_agent,
        pesquisador_agent,
        minerador_agent,
        copywriter_agent,
    ],
    # Permite CORS do agent-ui rodando em qualquer origem local ou Coolify
    add_cors_headers=True,
).get_app()
