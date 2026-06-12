import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.tavily import TavilyTools
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS

load_dotenv()

# 1. O Cérebro (Agora com Banco de Dados para Memória)
agente_pesquisador = Agent(
    name="Pesquisador Financeiro",
    model=Groq(id="qwen/qwen3-32b"), 
    tools=[TavilyTools()],
    db=SqliteDb(db_file="gotham_memory.db"), # Cria um arquivo local para salvar as conversas
    description="Tu és um Researcher avançado focado em mercado financeiro.",
    instructions=["Use tabelas para mostrar a informação final."],
    markdown=True,
    add_history_to_context=True, # Faz a IA ler o banco de dados antes de responder
)

# 2. A Mágica do AgentOS: Transformando o Agente em uma API
gotham_os = AgentOS(agents=[agente_pesquisador])

# 3. Exportando o aplicativo para o servidor rodar
app = gotham_os.get_app()