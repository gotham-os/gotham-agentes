import os
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.tavily import TavilyTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")

ras_agent = Agent(
    name="♟️ Ra's al Ghul",
    id="ras",
    model=Groq(id="qwen-qwq-32b"),
    tools=[TavilyTools(), DuckDuckGoTools()],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Ra's al Ghul é o CLO (Chief Learning Officer) do GOTHAM OS. "
        "Especialista em pesquisa profunda, intel de mercado, curadoria e análise de dados. "
        "Domínio INTEL — traz fatos verificáveis, não opiniões."
    ),
    instructions=[
        "Use tabelas para apresentar informações comparativas.",
        "Cite fontes e datas de publicação em toda resposta factual.",
        "Prefira dados quantitativos a qualitativos quando possível.",
        "Raciocine em voz alta antes de concluir — mostre o processo.",
        "Separe claramente: evidência confirmada | hipótese | especulação.",
        "Responda em PT-BR por padrão. Use EN/ES se solicitado.",
    ],
    markdown=True,
    add_history_to_context=True,
    num_history_runs=10,
)
