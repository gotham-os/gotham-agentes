import json
import os
from datetime import date
from pathlib import Path

from agno.agent import Agent
from agno.tools import tool
from lib.models import get_model
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")
_KNOWLEDGE = Path(os.getenv("GOTHAM_KNOWLEDGE_PATH", "./knowledge")) / "selina"
_OUTPUTS = Path(os.getenv("GOTHAM_OUTPUTS_PATH", "./outputs")) / "selina"


# ── Knowledge tools ───────────────────────────────────────────────────────────

_KNOWLEDGE_FILES = {
    "drc": "drc_framework.md",
    "hooks": "hooks_formulas.md",
    "headlines": "headlines_formulas.md",
    "swipe_file": "swipe_file.md",
    "vsl": "vsl_framework.md",
}

@tool(
    name="load_copy_knowledge",
    description=(
        "Carrega frameworks e insumos de copy do knowledge base da Selina. "
        "tipo: 'drc' | 'hooks' | 'headlines' | 'swipe_file' | 'vsl' | 'todos'"
    ),
)
def load_copy_knowledge(tipo: str = "todos") -> str:
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
    name="save_copy_output",
    description="Salva output de copy gerado (hooks, headline, VSL, ad copy). titulo em snake_case, conteudo em markdown.",
)
def save_copy_output(titulo: str, conteudo: str) -> str:
    _OUTPUTS.mkdir(parents=True, exist_ok=True)
    filename = f"{date.today().isoformat()}-{titulo}.md"
    filepath = _OUTPUTS / filename
    filepath.write_text(conteudo, encoding="utf-8")
    return json.dumps({"status": "saved", "path": str(filepath)})


@tool(
    name="list_copy_outputs",
    description="Lista outputs de copy já salvos pela Selina.",
)
def list_copy_outputs() -> str:
    if not _OUTPUTS.exists():
        return json.dumps({"outputs": [], "note": "Nenhum output salvo ainda."})
    files = sorted(_OUTPUTS.glob("*.md"), reverse=True)
    return json.dumps({"outputs": [f.name for f in files[:20]]})


# ── Agent ─────────────────────────────────────────────────────────────────────

selina_agent = Agent(
    name="💎 Selina Kyle",
    id="selina",
    model=get_model("selina", "llama-3.3-70b-versatile"),
    tools=[load_copy_knowledge, save_copy_output, list_copy_outputs],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Selina Kyle é a CMO (Chief Marketing Officer) do GOTHAM OS. "
        "Especialista em copy de resposta direta, VSL, headlines, hooks, quizzes e anúncios. "
        "Domínio: ofertas, funis e conversão. Conhece BR, ES (tier-1) e EN. "
        "Usa knowledge base própria com frameworks DRC, fórmulas e swipe file curado."
    ),
    instructions=[
        "ANTES de escrever qualquer copy, chame load_copy_knowledge para carregar os frameworks relevantes.",
        "Crie copy orientada a resultados, não a estética.",
        "Use a fórmula: Dor → Agitação → Solução em qualquer formato.",
        "Adapte o tom ao mercado: BR=emocional/direto, ES=formal/aspiracional, EN=data-driven.",
        "Sempre inclua CTAs claros e testáveis.",
        "Para quizzes, use perguntas que qualificam E geram curiosidade.",
        "Quando pedido, gere variações A/B para teste.",
        "Use gatilhos psicológicos e storytelling com precisão cirúrgica.",
        "Ao finalizar uma entrega, pergunte se quer salvar com save_copy_output.",
        "Responda em PT-BR por padrão. Mude idioma se o projeto exigir.",
    ],
    markdown=True,
    add_history_to_context=True,
    num_history_runs=5,
)
