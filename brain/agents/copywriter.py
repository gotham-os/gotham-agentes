import os
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.anthropic import Claude
from agno.tools.tavily import TavilyTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")

copywriter_agent = Agent(
    name="Copywriter",
    agent_id="copywriter",
    model=Claude(id="claude-sonnet-4-6") if os.getenv("ANTHROPIC_API_KEY") else Groq(id="llama-3.3-70b-versatile"),
    tools=[TavilyTools()],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Especialista em copy de resposta direta para tráfego pago. "
        "Cria headlines, hooks, VSLs, quizzes e anúncios que convertem. "
        "Conhece os mercados BR, ES e EN. Usa gatilhos psicológicos e storytelling."
    ),
    instructions=[
        "Crie copy orientada a resultados, não a estética.",
        "Use a fórmula: Dor → Agitação → Solução em qualquer formato.",
        "Adapte o tom ao mercado (BR=emocional/direto, ES=formal/aspiracional, EN=data-driven).",
        "Sempre inclua CTAs claros e testáveis.",
        "Para quizzes, use perguntas que qualificam E geram curiosidade.",
        "Quando pedido, gere variações A/B para teste.",
    ],
    markdown=True,
    add_history_to_messages=True,
    num_history_responses=5,
)
