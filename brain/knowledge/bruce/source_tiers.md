# Source Tiers — Peso de Fonte por Confiabilidade

> Calibração migrada de gotham-brainstorm/evidence_quality.py em 2026-06-13.
> Usado pelo `calculate_opportunity_score` tool e como guia de curadoria.

## Regra: _is_usable() gate

Um sinal só conta no score se `quality_score >= 62` (usable).
Qualidade < 62 = ruído — filtrado antes de calcular.

**Fatores de qualidade por sinal:**
- `source_tier * 0.45` — base pelo tier da fonte
- `+6` se tem URL auditável / `-12` se não tem URL
- `+14` se tem métricas numéricas / `-8` se sem métricas
- `+8` se strength = high/verified / `-8` se strength = low

## Tabela de Tiers (0-100)

| Fonte | Tier | Tipo de evidência |
|---|---|---|
| TrustMRR | 95 | Revenue — MRR confirmado |
| Baremetrics | 92 | Revenue — SaaS metrics |
| Stripe | 92 | Revenue — transações confirmadas |
| Acquire.com | 88 | Revenue — SaaS à venda com MRR |
| Flippa | 86 | Revenue — negócios à venda |
| AppSumo | 78 | Revenue — vendas lifetime deal |
| G2 | 76 | Pain — reviews B2B |
| Capterra | 76 | Pain — reviews B2B |
| SimilarWeb | 74 | Distribution — tráfego pago |
| SEMRush | 74 | Distribution — keywords pagas |
| Google Keyword Planner | 72 | Demand — volume de busca |
| Meta Ads Library | 72 | Distribution — anúncios ativos |
| Google Trends | 68 | Demand — interesse orgânico |
| TikTok Creative Center | 66 | Distribution — ads trending |
| Product Hunt | 62 | Demand — lançamentos |
| ReclameAqui | 60 | Pain — reclamações BR |
| Reddit | 58 | Pain — dores reais de comunidade |
| Hacker News | 55 | Pain/Demand — tech community |
| Tavily/DuckDuckGo | 45-50 | Mixed — busca web geral |
| Manual/sem fonte | 30 | Anedota — sem verificabilidade |

## Como usar ao pesquisar

1. **Prefira fontes de tier alto** — Meta Ads Library (72) vale mais que Reddit (58)
2. **Sempre capture a URL** — sinal sem link perde 12 pontos de qualidade
3. **Métricas numéricas dobram o valor** — "12 anunciantes ativos" vs "vi alguns anúncios"
4. **Cruzar fontes independentes** — Reddit + Meta Ads + Google Trends = confidence alta
5. **Strength "verified"** = compra confirmada, campanha escalada visivelmente ativa

## Critério de descarte de sinal

- Sem URL → desconfia (pode ser invenção)
- Reddit sem upvotes/posts contados → anedota (strength=low)
- Meta Ads sem `relevant_count` → não sabe se os anúncios são do nicho certo
- Fonte não mapeada acima → tier 45 (DuckDuckGo/busca genérica)
