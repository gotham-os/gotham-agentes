"""
Minerador de Ofertas Escaladas — agente Agno que garante oportunidades reais.

Fontes cobertas:
- Meta Ads Library (browser via MCP)
- TikTok Creative Center
- Reddit (API pública)
- Google Trends RSS (BR, ES, EN)
- ReclameAqui (scraping)
- Google Scholar / ScienceDaily
- Tavily deep research

Mercados: BR · ES (tier-1) · EN
"""
from __future__ import annotations

import json
import os
from html import unescape
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.anthropic import Claude
from agno.tools import tool
from agno.tools.tavily import TavilyTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.db.sqlite import SqliteDb

DB_PATH = os.getenv("GOTHAM_DB_PATH", "./gotham_memory.db")

# ── Custom tools ──────────────────────────────────────────────────────────────

@tool(name="google_trends", description="Busca tendências do Google Trends para um país (geo=BR|US|ES|MX etc)")
def google_trends(geo: str = "BR") -> str:
    url = f"https://trends.google.com/trending/rss?geo={quote(geo)}"
    req = Request(url, headers={"User-Agent": "gotham-minerador/0.1"})
    try:
        with urlopen(req, timeout=20) as resp:
            root = ElementTree.fromstring(resp.read())
        channel = root.find("channel")
        items = channel.findall("item") if channel else []
        ns = "https://trends.google.com/trending/rss"
        results = []
        for item in items[:15]:
            title = (item.find("title") or type("", (), {"text": ""})()).text or ""
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


@tool(name="reddit_search", description="Busca posts no Reddit sobre um termo. Útil para encontrar dores reais de consumidores.")
def reddit_search(query: str, limit: int = 10) -> str:
    url = f"https://www.reddit.com/search.json?q={quote(query)}&sort=top&t=month&limit={limit}"
    req = Request(url, headers={"User-Agent": "gotham-minerador/0.1 by local-agent"})
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
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "summary": (p.get("selftext") or "")[:200],
            })
        return json.dumps(posts, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool(name="reclameaqui_search", description="Busca reclamações no ReclameAqui sobre uma empresa ou produto. Excelente para mapear dores de mercado BR.")
def reclameaqui_search(query: str) -> str:
    import httpx
    url = f"https://iosearch.reclameaqui.com.br/raichu-io-site-search-api/query/companyComplains/0/10?callback=false&q={quote(query)}"
    try:
        resp = httpx.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        return resp.text[:2000]
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool(name="meta_ads_search", description="Pesquisa na Meta Ads Library por anúncios ativos em um país. Retorna dados sobre anunciantes escalando.")
def meta_ads_search(query: str, country: str = "BR") -> str:
    """
    Usa a API pública da Meta Ads Library.
    Para scraping com login usa gotham-browser (MCP).
    """
    # API pública (sem token) - retorna resultados limitados mas válidos
    url = (
        f"https://www.facebook.com/ads/library/api/?search_terms={quote(query)}"
        f"&ad_type=ALL&countries%5B%5D={country}&active_status=active&media_type=all"
    )
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; gotham-bot/0.1)"})
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        return json.dumps(data, ensure_ascii=False)[:3000]
    except Exception as exc:
        # API pública bloqueia sem token - retornar instrução para usar browser
        return json.dumps({
            "info": "Meta Ads Library requer navegador com login para dados completos.",
            "action": "Use gotham-browser MCP: acesse https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=BR&q=" + quote(query),
            "error": str(exc),
        })


@tool(name="tiktok_trends", description="Busca hashtags e anúncios em tendência no TikTok Creative Center.")
def tiktok_trends(country: str = "BR") -> str:
    """TikTok Creative Center hashtag trends via API pública."""
    url = f"https://ads.tiktok.com/creative-center/api/v1/hashtag/rank/list/?industry_id=&country_code={country}&period=7"
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://ads.tiktok.com/creative-center/trends/hashtag/pad/en",
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

SYSTEM_PROMPT = """Você é um analista frio de oportunidades digitais escaláveis.
Seu trabalho não é gerar ideias bonitas; é encontrar apostas assimétricas que possam virar caixa rapidamente.

## Regras
1. Aceite qualquer formato digital escalável: SaaS, micro-SaaS, automação, template, ebook, curso, comunidade, newsletter, API, serviço productizado digital.
2. Rejeite produtos físicos, estoque, logística, operação presencial.
3. Separe evidências de opiniões. Toda recomendação precisa ter links, fonte e tipo de evidência.
4. Não confunda hype com oportunidade. Trend só importa se puder ser ligada a dor + comprador + promessa + teste.
5. Prefira entrega manual digital antes de construir software.
6. Sempre inclua red team: por que a tese pode estar errada?
7. Sempre defina critério de matar e critério de escalar.

## Famílias de evidência
- Distribuição: Meta Ads Library, TikTok Creative Center, Google Ads → anúncios ativos = prova de caixa
- Dor: Reddit, ReclameAqui, X.com, G2, Capterra → reclamações reais
- Demanda: Google Trends, YouTube → interesse orgânico
- Gap: existe fora, falta adaptação BR/LATAM ou versão simples

## Para cada oportunidade encontrada, estruture assim:
```json
{
  "title": "Nome",
  "mercados": ["BR", "ES", "EN"],
  "decision": "TESTAR AGORA | DEEPDIVE | RADAR | DESCARTAR",
  "score_geral": 0-100,
  "comprador": "quem compra",
  "dor": "dor urgente",
  "promessa": "promessa testável",
  "evidencias": ["fonte + resumo"],
  "mvp": ["3 entregáveis máximos"],
  "teste_meta_ads": {"budget": "R$300-R$700", "kill_rule": "...", "scale_rule": "..."},
  "red_team": ["riscos reais"]
}
```

## Frase-guia
Não pergunte "essa ideia é interessante?". Pergunte: "isso merece 72h de execução e R$300-R$1000 de teste?"
"""

minerador_agent = Agent(
    name="Minerador de Ofertas",
    agent_id="minerador",
    model=Claude(id="claude-sonnet-4-6") if os.getenv("ANTHROPIC_API_KEY") else Groq(id="llama-3.3-70b-versatile"),
    tools=[
        TavilyTools(),
        DuckDuckGoTools(),
        google_trends,
        reddit_search,
        reclameaqui_search,
        meta_ads_search,
        tiktok_trends,
    ],
    db=SqliteDb(db_file=DB_PATH),
    description=(
        "Especialista em encontrar ofertas digitais escaladas no Brasil, mercados hispânicos e inglês. "
        "Usa Meta Ads Library, TikTok, Reddit, ReclameAqui e Google Trends para confirmar o que está convertendo agora."
    ),
    instructions=[
        "Sempre pesquise em pelo menos 3 fontes antes de concluir sobre uma oportunidade.",
        "Para mercado ES (espanhol tier-1), foque em México, Colômbia, Espanha.",
        "Para mercado BR, use ReclameAqui e Reddit BR para validar dores.",
        "Para mercado EN, use Reddit e TrustPilot.",
        "Use Tavily para pesquisa web profunda quando precisar de dados recentes.",
        "Estruture a saída final em JSON seguindo o schema do sistema.",
        "Mínimo 5 oportunidades por rodada quando há evidência suficiente.",
    ],
    system_message=SYSTEM_PROMPT,
    markdown=True,
    add_history_to_messages=True,
    num_history_responses=5,
)
