"""
Bruce Wayne — CEO / Minerador de Oportunidades Escaladas.
Domínio: ROI, radar de apostas assimétricas, validação de mercado.

Fontes cobertas:
- Meta Ads Library (browser via MCP)
- TikTok Creative Center
- Reddit (API pública)
- Google Trends RSS (BR, ES, EN)
- ReclameAqui (scraping)
- Tavily deep research
- DuckDuckGo

Mercados: BR · ES (tier-1) · EN

Pipeline obrigatório:
  1. load_scoring_knowledge   — carrega rubrica + tiers + fórmulas
  2. [ferramentas de coleta]  — Meta Ads, Reddit, Trends, etc.
  3. calculate_opportunity_score — score determinístico por oportunidade
  4. save_opportunity_output  — persiste resultado em /knowledge/bruce/outputs/
"""
from __future__ import annotations

import httpx
import json
import os
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from agno.agent import Agent
from agno.tools import tool
from lib.models import get_model
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.db.sqlite import SqliteDb

from lib.scoring import score_opportunity

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")
_KNOWLEDGE = Path(os.getenv("GOTHAM_KNOWLEDGE_PATH", "./knowledge")) / "bruce"
_OUTPUTS = Path(os.getenv("GOTHAM_OUTPUTS_PATH", "./outputs")) / "bruce"

_KNOWLEDGE_FILES = {
    "rubric": "scoring_rubric.md",
    "tiers": "source_tiers.md",
    "formulas": "scoring_formulas.md",
}

# ── Knowledge tools ───────────────────────────────────────────────────────────

@tool(
    name="load_scoring_knowledge",
    description=(
        "SEMPRE chamar PRIMEIRO antes de pesquisar. "
        "Carrega rubrica de decisão, tiers de fonte e fórmulas de scoring. "
        "tipo: 'rubric'|'tiers'|'formulas'|'todos'"
    ),
)
def load_scoring_knowledge(tipo: str = "todos") -> str:
    _KNOWLEDGE.mkdir(parents=True, exist_ok=True)
    if tipo == "todos":
        files = list(_KNOWLEDGE_FILES.items())
    else:
        if tipo not in _KNOWLEDGE_FILES:
            return f"Tipo inválido: {tipo}. Use: {list(_KNOWLEDGE_FILES.keys())} ou 'todos'."
        files = [(tipo, _KNOWLEDGE_FILES[tipo])]

    parts: list[str] = []
    for name, fname in files:
        path = _KNOWLEDGE / fname
        if path.exists():
            parts.append(f"## {name.upper()}\n{path.read_text(encoding='utf-8')}")
        else:
            parts.append(f"## {name.upper()}\n[arquivo não encontrado: {fname}]")
    return "\n\n---\n\n".join(parts)


@tool(
    name="calculate_opportunity_score",
    description=(
        "Calcula score determinístico de uma oportunidade usando algoritmo calibrado. "
        "Chamar após coletar evidências. Retorna score + decision + warnings. "
        "Input: JSON string com título, sinais coletados e metadados do MVP."
    ),
)
def calculate_opportunity_score(opportunity_json: str) -> str:
    """
    Input JSON schema:
    {
      "title": "Nome da oportunidade",
      "signals": [
        {
          "source": "meta ads library",   // fonte: ver source_tiers.md
          "evidence_type": "distribution", // revenue|pain|distribution|demand|trend|competitor|gap
          "strength": "high",              // low|medium|high|verified
          "has_url": true,                 // tem link auditável?
          "has_metrics": true,             // tem dados numéricos (contagem, MRR, score)?
          "relevant_count": 12,            // itens relevantes encontrados (anúncios, posts)
          "notes": "12 anunciantes ativos com criativos de gestão de tráfego BR"
        }
      ],
      "can_deliver_manually": true,
      "mvp_hours": 48,
      "is_digital": true,
      "solution_type": "productized_service"
    }
    """
    try:
        data = json.loads(opportunity_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"JSON inválido: {e}"})

    result = score_opportunity(data)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(
    name="save_opportunity_output",
    description="Salva resultado de oportunidade pesquisada em arquivo markdown.",
)
def save_opportunity_output(titulo: str, conteudo: str) -> str:
    _OUTPUTS.mkdir(parents=True, exist_ok=True)
    slug = titulo.lower().replace(" ", "_").replace("/", "-")[:40]
    filename = f"{date.today().isoformat()}-{slug}.md"
    path = _OUTPUTS / filename
    path.write_text(f"# {titulo}\n\n{conteudo}", encoding="utf-8")
    return f"Salvo: {path}"


@tool(
    name="list_opportunity_outputs",
    description="Lista oportunidades já pesquisadas e salvas.",
)
def list_opportunity_outputs() -> str:
    _OUTPUTS.mkdir(parents=True, exist_ok=True)
    files = sorted(_OUTPUTS.glob("*.md"), reverse=True)
    if not files:
        return "Nenhum output salvo ainda."
    return "\n".join(f.name for f in files[:20])


# ── Market research tools ─────────────────────────────────────────────────────

@tool(
    name="google_trends",
    description="Busca tendências do Google Trends. geo=BR|US|ES|MX|CO. Source tier: 68.",
)
def google_trends(geo: str = "BR") -> str:
    url = f"https://trends.google.com/trending/rss?geo={quote(geo)}"
    req = Request(url, headers={"User-Agent": "gotham-minerador/1.0"})
    try:
        with urlopen(req, timeout=20) as resp:
            root = ElementTree.fromstring(resp.read())
        channel = root.find("channel")
        items = channel.findall("item") if channel else []
        ns = "https://trends.google.com/trending/rss"
        results = []
        for item in items[:15]:
            title_el = item.find("title")
            title = (title_el.text or "") if title_el is not None else ""
            traffic_el = item.find(f"{{{ns}}}approx_traffic")
            traffic = traffic_el.text if traffic_el is not None else "N/A"
            news = [
                (el.text or "")
                for el in item.findall(f"{{{ns}}}news_item/{{{ns}}}news_item_title")
            ]
            results.append({"trend": unescape(title), "traffic": traffic, "news": news[:2]})
        return json.dumps(results, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool(
    name="reddit_search",
    description=(
        "Busca posts no Reddit sobre um termo. "
        "Útil para dores reais de consumidores. Source tier: 58. "
        "Inclua subreddit específico para melhor precisão: 'query subreddit:entrepreneur'."
    ),
)
def reddit_search(query: str, limit: int = 10) -> str:
    url = f"https://www.reddit.com/search.json?q={quote(query)}&sort=top&t=month&limit={limit}"
    req = Request(url, headers={"User-Agent": "gotham-minerador/1.0 by local-agent"})
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        posts = []
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            posts.append({
                "title": p.get("title", ""),
                "subreddit": p.get("subreddit", ""),
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "summary": (p.get("selftext") or "")[:300],
            })
        return json.dumps(posts, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool(
    name="reclameaqui_search",
    description=(
        "Busca reclamações no ReclameAqui sobre empresa ou produto. "
        "Excelente para mapear dores de mercado BR. Source tier: 60."
    ),
)
def reclameaqui_search(query: str) -> str:
    url = (
        f"https://iosearch.reclameaqui.com.br/raichu-io-site-search-api/query/"
        f"companyComplains/0/10?callback=false&q={quote(query)}"
    )
    try:
        resp = httpx.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        return resp.text[:2000]
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool(
    name="meta_ads_search",
    description=(
        "Pesquisa anúncios ATIVOS na Meta Ads Library via browser real (gotham-browser). "
        "Retorna lista de anunciantes e quantidade de anúncios ativos para a query — "
        "prova de distribuição/escala. Source tier: 72."
    ),
)
def meta_ads_search(query: str, country: str = "BR") -> str:
    browser_url = os.getenv("GOTHAM_BROWSER_URL", "http://gotham-browser:7893")
    lib_url = (
        f"https://www.facebook.com/ads/library/?active_status=active"
        f"&ad_type=all&country={country}&q={quote(query)}"
    )
    task = (
        f"Go to {lib_url} and extract the names of up to 10 advertisers shown "
        f"and how many active ads each has. Return as a JSON list of "
        f'{{"advertiser": str, "ads": int}}.'
    )
    try:
        resp = httpx.post(
            f"{browser_url}/run",
            json={"task": task, "llm_provider": "nvidia", "max_steps": 15},
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return json.dumps({"error": data.get("error"), "source": "meta_ads_library", "url": lib_url})
        return json.dumps({"source": "meta_ads_library", "url": lib_url, "result": data.get("result")}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({
            "info": "gotham-browser indisponível.",
            "action": f"Consultar manualmente: {lib_url}",
            "error": str(exc),
        })


@tool(
    name="meta_ads_scale_scan",
    description=(
        "Varre a Meta Ads Library (browser real, scroll profundo) procurando ofertas "
        "JÁ ESCALANDO para a query dada — versão mais agressiva do meta_ads_search, "
        "focada em achar Pages com 100+ anúncios ativos OU clusters de Pages diferentes "
        "promovendo a MESMA oferta (escala distribuída). country: 'BR'|'US'|'MX'|'CO'|'ES' etc. "
        "Flag HIGH PRIORITY = 100+ anúncios ativos (mesma Page ou soma do cluster). "
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
            timeout=600,
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


def _scale_scan_task(query: str, country: str) -> str:
    lib_url = (
        f"https://www.facebook.com/ads/library/?active_status=active"
        f"&ad_type=all&country={country}&q={quote(query)}"
    )
    return (
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


@tool(
    name="meta_ads_scale_scan_batch",
    description=(
        "Varre a Meta Ads Library EM PARALELO para múltiplas queries/países de uma vez. "
        "Usa /run-batch do gotham-browser: cada scan roda em BrowserSession independente "
        "com LLM provider diferente (nvidia/zen-free/gemini) para evitar rate limit. "
        "Muito mais rápido que chamar meta_ads_scale_scan N vezes sequencialmente. "
        "queries_countries: lista de objetos {query: str, country: str}. "
        "Retorna lista de resultados na mesma ordem. "
        "Critério de escala: Page única com 100+ ads OU cluster de Pages com mesma oferta somando 100+. "
        "Source tier: 72."
    ),
)
def meta_ads_scale_scan_batch(queries_countries: list[dict]) -> str:
    browser_url = os.getenv("GOTHAM_BROWSER_URL", "http://gotham-browser:7893")
    tasks = []
    meta = []
    for item in queries_countries:
        q = item.get("query", "")
        c = item.get("country", "BR")
        lib_url = (
            f"https://www.facebook.com/ads/library/?active_status=active"
            f"&ad_type=all&country={c}&q={quote(q)}"
        )
        tasks.append({
            "task": _scale_scan_task(q, c),
            "max_steps": 25,
            "id": f"{c}:{q}",
        })
        meta.append({"query": q, "country": c, "url": lib_url})

    try:
        resp = httpx.post(
            f"{browser_url}/run-batch",
            json={"tasks": tasks},
            timeout=720,
        )
        resp.raise_for_status()
        results = resp.json()
        output = []
        for i, (res, m) in enumerate(zip(results, meta)):
            if res.get("ok"):
                output.append({
                    "source": "meta_ads_library",
                    "country": m["country"],
                    "query": m["query"],
                    "url": m["url"],
                    "llm_provider_used": res.get("llm_provider_used"),
                    "result": res.get("result"),
                })
            else:
                output.append({
                    "source": "meta_ads_library",
                    "country": m["country"],
                    "query": m["query"],
                    "url": m["url"],
                    "error": res.get("error"),
                })
        return json.dumps(output, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc), "tip": "Verificar gotham-browser /health"})


@tool(
    name="tiktok_trends",
    description=(
        "Busca hashtags em tendência no TikTok Creative Center. "
        "Source tier: 66."
    ),
)
def tiktok_trends(country: str = "BR") -> str:
    url = (
        f"https://ads.tiktok.com/creative-center/api/v1/hashtag/rank/list/"
        f"?industry_id=&country_code={country}&period=7"
    )
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://ads.tiktok.com/creative-center/trends/hashtag/",
    })
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        return json.dumps(data, ensure_ascii=False)[:2000]
    except Exception as exc:
        return json.dumps({
            "info": "TikTok Creative Center — consulte manualmente: https://ads.tiktok.com/business/creativecenter/inspiration/topads/",
            "error": str(exc),
        })


# ── Agent definition ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é Bruce Wayne — CEO do GOTHAM OS e analista frio de oportunidades digitais escaláveis.
Seu trabalho não é gerar ideias bonitas: é encontrar apostas assimétricas que possam virar caixa rapidamente.

## Protocolo obrigatório (SEMPRE nesta ordem)

1. **load_scoring_knowledge("todos")** — carregar rubrica + tiers + fórmulas ANTES de pesquisar
2. **Pesquisar em mínimo 3 fontes independentes** usando as tools disponíveis
3. **calculate_opportunity_score** — calcular score determinístico para CADA oportunidade
4. **save_opportunity_output** — persistir o resultado final

## Regras de coleta

1. Aceite qualquer formato digital escalável: SaaS, micro-SaaS, automação, template, ebook, curso, comunidade, newsletter, API, serviço productizado.
2. Rejeite produtos físicos, estoque, logística, operação presencial.
3. Separe evidências de opiniões. Toda evidência precisa de fonte + URL + métrica numérica.
4. Não confunda hype com oportunidade. Trend só importa se ligada a dor + comprador + promessa + teste.
5. Prefira entrega manual digital antes de construir software.
6. Sempre red team: por que a tese pode estar errada?
7. Sempre defina critério de matar e critério de escalar.

## Famílias de evidência (em ordem de confiabilidade)

- **Revenue**: TrustMRR, Acquire, Flippa, AppSumo, Stripe → prova de caixa real
- **Distribution**: Meta Ads Library, TikTok CC → anúncios ativos = alguém gasta nisto
- **Pain**: Reddit, ReclameAqui, G2, Capterra → dores reais com volume
- **Demand**: Google Trends, YouTube → interesse orgânico crescente
- **Gap**: existe fora, falta versão BR/ES ou versão mais simples

## Output por oportunidade (após calculate_opportunity_score)

```json
{
  "title": "Nome",
  "mercados": ["BR", "ES", "EN"],
  "decision": "[resultado do calculate_opportunity_score]",
  "scores": "[resultado do calculate_opportunity_score]",
  "comprador": "quem compra — específico",
  "dor": "dor urgente e específica",
  "promessa": "promessa testável em 1 frase",
  "evidencias": [{"fonte": "...", "url": "...", "resumo": "..."}],
  "mvp": ["máximo 3 entregáveis para validar"],
  "meta_ads_test": {"budget": "R$300–R$700", "kill_rule": "...", "scale_rule": "..."},
  "red_team": ["por que a tese pode estar errada"]
}
```

## Frase-guia

> "Não pergunte: 'essa ideia é interessante?'. Pergunte: 'isso merece 72h de execução e R$300–R$1.000 de teste?'"
"""

bruce_agent = Agent(
    name="🏛️ Bruce Wayne",
    id="bruce",
    model=get_model("bruce", "llama-3.3-70b-versatile"),
    tools=[
        # Knowledge (sempre primeiro)
        load_scoring_knowledge,
        calculate_opportunity_score,
        save_opportunity_output,
        list_opportunity_outputs,
        # Research
        TavilyTools(),
        DuckDuckGoTools(),
        google_trends,
        reddit_search,
        reclameaqui_search,
        meta_ads_search,
        meta_ads_scale_scan,
        meta_ads_scale_scan_batch,
        tiktok_trends,
    ],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Bruce Wayne é o CEO do GOTHAM OS — domínio ROI, estratégia e oportunidades de mercado. "
        "Especialista em encontrar apostas assimétricas digitais escaláveis (BR, ES tier-1, EN). "
        "Usa scoring algébrico calibrado (SOURCE_TIERS + fórmulas) para decisões determinísticas."
    ),
    instructions=[
        "PRIMEIRO: sempre chamar load_scoring_knowledge('todos') antes de qualquer pesquisa.",
        "Pesquisar em mínimo 3 fontes independentes antes de concluir sobre uma oportunidade.",
        "SEMPRE chamar calculate_opportunity_score após coletar evidências — nunca inventar score.",
        "Para mercado ES (espanhol tier-1): focar em México, Colômbia, Espanha.",
        "Para mercado BR: usar ReclameAqui e Reddit BR para validar dores.",
        "Para mercado EN: usar Reddit e Tavily para pesquisa em inglês.",
        "Quando o pedido for caça-escala (achar ofertas com 100+ anúncios ativos, "
        "única Page ou cluster de Pages diferentes promovendo a mesma oferta), use "
        "meta_ads_scale_scan_batch com TODAS as queries+países de uma vez (uma única chamada) "
        "em vez de chamar meta_ads_scale_scan individualmente N vezes. "
        "meta_ads_scale_scan_batch roda todas em paralelo com BrowserSession independente por scan — "
        "muito mais rápido e sem rate limit. "
        "Só reporte achados com 100+ anúncios (Page única ou soma de cluster) como 'escalando' — "
        "abaixo disso é só 'tem anúncio'.",
        "Entregar mínimo 5 oportunidades rankeadas por score quando há evidência suficiente.",
        "Salvar resultado final com save_opportunity_output.",
    ],
    system_message=SYSTEM_PROMPT,
    markdown=True,
    add_history_to_context=True,
    num_history_runs=5,
)
