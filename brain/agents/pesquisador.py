import os
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.tavily import TavilyTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")

pesquisador_agent = Agent(
    name="Pesquisador",
    agent_id="pesquisador",
    model=Groq(id="qwen/qwen3-32b"),
    tools=[TavilyTools()],
    db=SqliteDb(db_file=DB_PATH),
    description="Pesquisador avançado com foco em mercado, tendências e dados verificáveis.",
    instructions=[
        "Use tabelas para apresentar informações comparativas.",
        "Cite fontes e datas de publicação.",
        "Prefira dados quantitativos a qualitativos quando possível.",
    ],
    markdown=True,
    add_history_to_messages=True,
    num_history_responses=10,
)
