import json
import os
from datetime import date
from pathlib import Path

from agno.agent import Agent
from agno.tools import tool
from lib.models import get_model
from agno.tools.tavily import TavilyTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")
_KNOWLEDGE = Path(os.getenv("GOTHAM_KNOWLEDGE_PATH", "./knowledge")) / "ras"
_OUTPUTS = Path(os.getenv("GOTHAM_OUTPUTS_PATH", "./outputs")) / "ras"

_KNOWLEDGE_FILES = {
    "frameworks": "research_frameworks.md",
    "fontes": "fontes_confiveis.md",
    "templates": "research_templates.md",
}


# ── Knowledge tools ───────────────────────────────────────────────────────────

@tool(
    name="load_research_knowledge",
    description=(
        "Carrega frameworks e metodologias de pesquisa do knowledge base do Ra's. "
        "tipo: 'frameworks' | 'fontes' | 'templates' | 'todos'"
    ),
)
def load_research_knowledge(tipo: str = "todos") -> str:
    if tipo == "todos":
        targets = list(_KNOWLEDGE_FILES.items())
    elif tipo in _KNOWLEDGE_FILES:
        targets = [(tipo, _KNOWLEDGE_FILES[tipo])]
    else:
        return json.dumps({"error": f"tipo inválido: '{tipo}'. Válidos: {list(_KNOWLEDGE_FILES)} | todos"})

    sections = []
    for key, fname in targets:
        path = _KNOWLEDGE / fname
        if path.exists():
            sections.append(f"## [{key}] {fname}\n\n{path.read_text(encoding='utf-8')}")
        else:
            sections.append(f"## [{key}] {fname}\n\n⚠️ Arquivo não encontrado. Adicione insumos em: `{path}`")

    return "\n\n---\n\n".join(sections)


@tool(
    name="save_research_output",
    description="Salva output de pesquisa/intel gerado. titulo em snake_case, conteudo em markdown.",
)
def save_research_output(titulo: str, conteudo: str) -> str:
    _OUTPUTS.mkdir(parents=True, exist_ok=True)
    filename = f"{date.today().isoformat()}-{titulo}.md"
    filepath = _OUTPUTS / filename
    filepath.write_text(conteudo, encoding="utf-8")
    return json.dumps({"status": "saved", "path": str(filepath)})


@tool(
    name="list_research_outputs",
    description="Lista pesquisas já salvas pelo Ra's.",
)
def list_research_outputs() -> str:
    if not _OUTPUTS.exists():
        return json.dumps({"outputs": [], "note": "Nenhum output salvo ainda."})
    files = sorted(_OUTPUTS.glob("*.md"), reverse=True)
    return json.dumps({"outputs": [f.name for f in files[:20]]})


# ── Agent ─────────────────────────────────────────────────────────────────────

ras_agent = Agent(
    name="♟️ Ra's al Ghul",
    id="ras",
    model=get_model("ras", "qwen-qwq-32b"),
    tools=[
        TavilyTools(),
        DuckDuckGoTools(),
        load_research_knowledge,
        save_research_output,
        list_research_outputs,
    ],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Ra's al Ghul é o CLO (Chief Learning Officer) do GOTHAM OS. "
        "Especialista em pesquisa profunda, intel de mercado, curadoria e análise de dados. "
        "Domínio INTEL — traz fatos verificáveis com fontes e datas. "
        "Usa knowledge base própria com frameworks de pesquisa e fontes confiáveis catalogadas."
    ),
    instructions=[
        "ANTES de pesquisar externamente, carregue os frameworks com load_research_knowledge.",
        "Use tabelas para apresentar informações comparativas.",
        "Cite fontes e datas de publicação em toda resposta factual.",
        "Prefira dados quantitativos a qualitativos quando possível.",
        "Raciocine em voz alta antes de concluir — mostre o processo.",
        "Separe claramente: evidência confirmada | hipótese | especulação.",
        "Ao finalizar uma pesquisa relevante, salve com save_research_output.",
        "Responda em PT-BR por padrão. Use EN/ES se solicitado.",
    ],
    markdown=True,
    add_history_to_context=True,
    num_history_runs=10,
)
