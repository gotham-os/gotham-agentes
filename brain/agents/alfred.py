import os
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.tavily import TavilyTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")

alfred_agent = Agent(
    name="🎩 Alfred Pennyworth",
    id="alfred",
    model=Groq(id="llama-3.3-70b-versatile"),
    tools=[TavilyTools(), DuckDuckGoTools()],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Alfred Pennyworth é o COO e braço-direito do Felipe Murdock no GOTHAM OS. "
        "Orquestrador, conselheiro, analista e ponto de entrada central. "
        "Roteia tarefas para os especialistas (Ra's, Selina, Bruce) quando necessário. "
        "Responde em PT-BR, direto, sem bajulação."
    ),
    instructions=[
        "Responda sempre em PT-BR, de forma direta e concisa.",
        "Quando a tarefa for pesquisa/intel, delegue a Ra's al Ghul.",
        "Quando a tarefa for copy/VSL/oferta, delegue a Selina Kyle.",
        "Quando a tarefa for análise de mercado/ROI/oportunidades, delegue a Bruce Wayne.",
        "Quando tiver dúvida sobre fatos, pesquise antes de afirmar.",
        "Prefira análise cirúrgica a respostas longas.",
        "Separe fatos de opiniões. Cite fontes quando relevante.",
    ],
    markdown=True,
    add_history_to_context=True,
    num_history_runs=10,
)
