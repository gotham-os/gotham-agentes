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
from agno.os.app import AgentOS
from agents import alfred_agent, minerador_agent, copywriter_agent, pesquisador_agent

app = AgentOS(
    name="GOTHAM Brain",
    agents=[
        alfred_agent,
        pesquisador_agent,
        minerador_agent,
        copywriter_agent,
    ],
    # Permite CORS do agent-ui rodando em qualquer origem
    cors_allowed_origins=["*"],
).get_app()
