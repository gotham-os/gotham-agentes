import os
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.anthropic import Claude
from agno.tools.tavily import TavilyTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")

alfred_agent = Agent(
    name="Alfred",
    id="alfred",
    model=Claude(id="claude-sonnet-4-6") if os.getenv("ANTHROPIC_API_KEY") else Groq(id="llama-3.3-70b-versatile"),
    tools=[TavilyTools(), DuckDuckGoTools()],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Alfred é o braço-direito estratégico do Felipe Murdock no GOTHAM OS. "
        "Conselheiro, analista e orquestrador. Responde em PT-BR, direto, sem bajulação."
    ),
    instructions=[
        "Responda sempre em PT-BR, de forma direta e concisa.",
        "Quando tiver dúvida sobre fatos, pesquise antes de afirmar.",
        "Prefira análise cirúrgica a respostas longas.",
        "Separe fatos de opiniões. Cite fontes quando relevante.",
    ],
    markdown=True,
    add_history_to_context=True,
    num_history_runs=10,
)
