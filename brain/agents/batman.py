"""
Batman — Vigia da Meta Ads Library.

Domínio: caça EXCLUSIVA a ofertas que JÁ ESTÃO ESCALANDO, com prova direta
via Meta Ads Library. Não garimpa "oportunidades" genéricas (isso é trabalho
do Bruce) — só confirma ESCALA REAL:

  - um anunciante/Page com 100+ anúncios ativos simultâneos, OU
  - o mesmo produto/oferta rodando em várias fanpages/contas diferentes
    (cluster de escala), somando 100+ anúncios ativos no total.

Mercados: BR · EN (US) · ES tier-1 (MX/CO/ES)

Pipeline obrigatório:
  1. meta_ads_scale_scan          — varre a Ads Library por mercado/query (browser real)
  2. calculate_opportunity_score  — score determinístico (mesma fórmula do Bruce)
  3. save_opportunity_output       — persiste achados em /outputs/batman/
"""
from __future__ import annotations

import httpx
import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import quote

from agno.agent import Agent
from agno.tools import tool
from agno.db.sqlite import SqliteDb

from lib.models import get_model
from lib.scoring import score_opportunity

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")
_OUTPUTS = Path(os.getenv("GOTHAM_OUTPUTS_PATH", "./outputs")) / "batman"


# ── Meta Ads Library — caça de escala ───────────────────────────────────────

@tool(
    name="meta_ads_scale_scan",
    description=(
        "Varre a Meta Ads Library (browser real via gotham-browser) procurando ofertas "
        "JÁ ESCALANDO para a query dada. country: 'BR'|'US'|'MX'|'CO'|'ES' etc. "
        "Retorna lista de Pages com contagem de anúncios ativos, e clusters de Pages "
        "diferentes que parecem promover a MESMA oferta (escala distribuída). "
        "Flag HIGH PRIORITY = 100+ anúncios ativos (mesma Page ou cluster). "
        "Source tier: 72."
    ),
)
def meta_ads_scale_scan(query: str, country: str = "BR") -> str:
    browser_url = os.getenv("GOTHAM_BROWSER_URL", "http://gotham-browser:7893")
    lib_url = (
        f"https://www.facebook.com/ads/library/?active_status=active"
        f"&ad_type=all&country={country}&q={quote(query)}"
    )
    task = (
        f"Go to {lib_url} (Meta Ads Library). Scroll down at least 6 times to load more results. "
        f"For EACH distinct advertiser/Page you see, record its name and the number of active ads "
        f"shown for that page (look for text like 'X anúncios'/'X ads' near the page name, or open "
        f"'Ver detalhes do anúncio'/'See ad details' to find the total active ads for that page). "
        f"Flag any advertiser with 100 or more active ads as HIGH PRIORITY. "
        f"Also check if multiple DIFFERENT page names appear to be promoting the SAME product or "
        f"offer (same product name, same creative/headline/image pattern) — group these together "
        f"as a 'scaling cluster' and sum their ad counts. "
        f"Return ONLY a JSON object, no extra text: "
        f'{{"pages": [{{"name": str, "ads_count": int}}], '
        f'"scaling_clusters": [{{"offer": str, "pages": [str], "total_ads": int}}]}}'
    )
    try:
        resp = httpx.post(
            f"{browser_url}/run",
            json={"task": task, "llm_provider": "nvidia", "max_steps": 25},
            timeout=240,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return json.dumps({"error": data.get("error"), "source": "meta_ads_library", "url": lib_url})
        return json.dumps({
            "source": "meta_ads_library",
            "country": country,
            "query": query,
            "url": lib_url,
            "result": data.get("result"),
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({
            "info": "gotham-browser indisponível.",
            "action": f"Consultar manualmente: {lib_url}",
            "error": str(exc),
        })


# ── Scoring / persistência (mesma fórmula e convenção do Bruce) ─────────────

@tool(
    name="calculate_opportunity_score",
    description=(
        "Calcula score determinístico de uma oferta escalando (mesmo algoritmo do Bruce). "
        "Input: JSON com title, signals (evidence_type='distribution', source='meta ads library', "
        "strength='verified'|'high', has_url=true, has_metrics=true, "
        "relevant_count=total de anúncios ativos confirmados), mvp_hours, solution_type, etc."
    ),
)
def calculate_opportunity_score(opportunity_json: str) -> str:
    try:
        data = json.loads(opportunity_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"JSON inválido: {e}"})
    return json.dumps(score_opportunity(data), ensure_ascii=False, indent=2)


@tool(
    name="save_opportunity_output",
    description="Salva oferta escalando encontrada em arquivo markdown.",
)
def save_opportunity_output(titulo: str, conteudo: str) -> str:
    _OUTPUTS.mkdir(parents=True, exist_ok=True)
    slug = titulo.lower().replace(" ", "_").replace("/", "-")[:40]
    filename = f"{date.today().isoformat()}-{slug}.md"
    path = _OUTPUTS / filename
    path.write_text(f"# {titulo}\n\n{conteudo}", encoding="utf-8")
    return json.dumps({"status": "saved", "path": str(path)})


@tool(
    name="list_opportunity_outputs",
    description="Lista ofertas escalando já salvas pelo Batman.",
)
def list_opportunity_outputs() -> str:
    if not _OUTPUTS.exists():
        return json.dumps({"outputs": [], "note": "Nenhum output salvo ainda."})
    files = sorted(_OUTPUTS.glob("*.md"), reverse=True)
    return json.dumps({"outputs": [f.name for f in files[:20]]})


# ── Agent definition ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é Batman — o Vigia do GOTHAM OS.

Seu trabalho é UM SÓ: patrulhar a Meta Ads Library (BR, EN/US, ES tier-1 = MX/CO/ES)
caçando ofertas que JÁ ESTÃO ESCALANDO — prova de volume real, agora, hoje.

## Critério de entrada (NÃO negociável)

Uma oferta só entra no seu relatório se houver evidência de uma das duas coisas:

1. **Page única com 100+ anúncios ativos simultâneos** — alguém está testando/escalando
   pesado uma única conta.
2. **Cluster de escala**: a MESMA oferta/produto (mesmo nome, mesma promessa, mesmo
   padrão de criativo) rodando em VÁRIAS Pages/contas diferentes, cuja soma de
   anúncios ativos passa de 100. Isso é típico de redes de afiliados, agências
   replicando a mesma oferta em contas-fantasma, ou marcas com múltiplas fanpages
   regionais — TODOS são sinal de produto validado.

Qualquer coisa abaixo de 100 anúncios (Page única ou cluster) NÃO é "escalando" —
é só "tem anúncio". Não reporte. Isso é trabalho do Bruce (radar de oportunidades),
não seu.

## O que você NÃO faz

- Não pesquisa Reddit, Trends, ReclameAqui, Tavily, DuckDuckGo, TikTok.
- Não infere "oportunidade" a partir de dor, tendência ou demanda.
- Não aceita "achei um anúncio interessante" como evidência — só conta volume.

## Pipeline obrigatório

1. **meta_ads_scale_scan(query, country)** — rode para várias queries/verticais
   em cada mercado (BR, US, MX no mínimo). Cubra pelo menos 3 verticais distintas
   por mercado antes de concluir (ex: saúde/suplementos, finanças/cripto,
   infoprodutos/educação, e-commerce/dropship, SaaS/apps).
2. Para CADA Page ou cluster com 100+ anúncios ativos, monte o sinal:
   `{"source": "meta ads library", "evidence_type": "distribution", "strength": "verified",
     "has_url": true, "has_metrics": true, "relevant_count": <ads_count ou total_ads>,
     "notes": "<nome da Page ou lista de Pages do cluster + descrição da oferta>"}`
3. **calculate_opportunity_score** — calcule o score para cada achado.
4. **save_opportunity_output** — persista o relatório final.

## Output

Para cada achado >= 100 anúncios:

```json
{
  "oferta": "nome/descrição do produto",
  "mercado": "BR|US|MX|...",
  "evidencia": {
    "tipo": "page_unica" | "cluster_escala",
    "pages": ["Nome da Page 1", "Nome da Page 2", "..."],
    "ads_total": 137,
    "url": "https://www.facebook.com/ads/library/?..."
  },
  "scores": "[resultado do calculate_opportunity_score]",
  "leitura": "por que isso está escalando — hipótese sobre o motivo (oferta forte, criativo vencedor, etc.)"
}
```

Ranqueie por `ads_total` (maior primeiro). Se NENHUMA oferta passar de 100 anúncios
em uma vertical/mercado, diga isso explicitamente — não force um achado fraco pra
parecer produtivo.

## Frase-guia

> "Eu não procuro ideias. Eu procuro o que já está rodando e ninguém está vendo."
"""

batman_agent = Agent(
    name="🦇 Batman",
    id="batman",
    model=get_model("batman", "openai/gpt-oss-120b"),
    tools=[
        meta_ads_scale_scan,
        calculate_opportunity_score,
        save_opportunity_output,
        list_opportunity_outputs,
    ],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Batman é o Vigia do GOTHAM OS — caça EXCLUSIVA a ofertas já escalando "
        "(100+ anúncios ativos) na Meta Ads Library, em uma única Page ou em "
        "cluster de Pages promovendo a mesma oferta. BR, EN (US) e ES tier-1 (MX/CO/ES). "
        "Não garimpa oportunidades genéricas — só confirma escala real com prova direta."
    ),
    instructions=[
        "Use meta_ads_scale_scan para BR, US e MX no mínimo, cobrindo pelo menos 3 verticais cada.",
        "Só reporte achados com 100+ anúncios ativos (Page única ou soma de cluster).",
        "Sempre monte o sinal com source='meta ads library', evidence_type='distribution', "
        "strength='verified', has_url=true, has_metrics=true antes de calculate_opportunity_score.",
        "Ranqueie achados por total de anúncios ativos, maior primeiro.",
        "Se uma vertical/mercado não tiver nada acima de 100, diga isso claramente — não infle achado fraco.",
        "Salve o relatório final com save_opportunity_output.",
        "Responda em PT-BR.",
    ],
    system_message=SYSTEM_PROMPT,
    markdown=True,
    add_history_to_context=True,
    num_history_runs=5,
)
