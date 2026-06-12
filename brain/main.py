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

from fastapi.middleware.cors import CORSMiddleware
from agno.os.app import AgentOS
from agents import alfred_agent, minerador_agent, copywriter_agent, pesquisador_agent

_cors_origins = os.getenv("CORS_ORIGINS", "https://agents.bmilimitada.com").split(",")

app = AgentOS(
    name="GOTHAM Brain",
    agents=[
        alfred_agent,
        pesquisador_agent,
        minerador_agent,
        copywriter_agent,
    ],
).get_app()

# Override CORS — AgentOS hardcodes allow_credentials=True que é incompatível com allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
