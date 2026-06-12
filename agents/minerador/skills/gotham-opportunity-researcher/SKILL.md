---
name: gotham-opportunity-researcher
description: Minerar oportunidades digitais escalaveis com evidencias, scoring, red team, MVP minimo e teste de Meta Ads. Use quando o usuario quiser pesquisar ideias de oferta, SaaS, micro-SaaS, infoprodutos, templates, auditorias, automacoes, data products ou servicos productizados digitais para gerar caixa rapido, validar com ads, criar kanban de MVPs ou rodar o radar local deste projeto.
---

# Gotham Opportunity Researcher

Use esta skill para transformar sinais de mercado em oportunidades digitais testaveis. O objetivo e gerar caixa rapido com entregas digitais escalaveis, nao produtos fisicos.

## Workflow

1. Fazer pesquisa market-first: nao assumir SaaS, IA, Brasil ou WhatsApp.
2. Aceitar apenas entregas digitais escalaveis: software, automacao, API, auditoria, template, planilha, relatorio, data product, ebook, curso, comunidade, newsletter ou servico productizado digital.
3. Rejeitar produto fisico, estoque, logistica, operacao presencial e oportunidades sem teste plausivel via Meta Ads.
4. Coletar sinais em `data/seeds/*.json`, agrupando pelo mesmo `cluster_key`.
5. Rodar o CLI Python:

```powershell
python -m opportunity_researcher.cli run --input data/seeds/first-test-signals.json --out data/reports/first-test.md --json-out data/opportunities/first-test.json
```

6. Ler o relatorio em `data/reports/`.
7. Para oportunidades `TESTAR AGORA`, gerar LP, criativos, oferta, MVP minimo e criterios de matar/escalar.

## Coletor Meta Ads Library

Para rodadas com Biblioteca de Anuncios, usar:

```powershell
.\.runtime\python\python.exe gotham_radar.py round-with-meta-ads --seed data/seeds/live-round-2026-05-13.json --queries-file data/meta_ads_queries.json --out data/raw/meta-ads-live.json --merged-seed-out data/seeds/live-round-with-meta-ads.json --report-out data/reports/live-round-with-meta-ads.md --json-out data/opportunities/live-round-with-meta-ads.json --kanban-out data/reports/live-round-with-meta-ads-kanban.html
```

O coletor usa Playwright/Edge via `scripts/meta_ads_playwright.mjs`, salva dados em `data/raw/` e snapshots em `data/raw/meta_ads_snapshots/`.

Se a Meta exigir login/captcha ou mudar o DOM, registrar a falha como baixa confianca e nao inferir escala.

## Fontes preferidas

- Receita: TrustMRR, Acquire, Flippa, AppSumo.
- Dor: Reddit, X, G2, Capterra, Reclame Aqui, Trustpilot, reviews de apps.
- Distribuicao: Meta Ads Library, TikTok Creative Center, Google Ads, Similarweb.
- Demanda: Google Trends, Keyword Planner, YouTube, Product Hunt.
- Arquivo: Wayback Machine para congelar evidencias.

## Regras de decisao

- `TESTAR AGORA`: LP + criativos + MVP minimo em ate 72h.
- `DEEPDIVE`: buscar mais evidencias antes de verba.
- `RADAR`: guardar e monitorar.
- `DESCARTAR`: nao gastar energia.

## Volume por rodada

Por padrao, cada rodada deve buscar no minimo 5 oportunidades promissoras e ranquear ate 12. Se houver menos de 5 com evidencia suficiente, declarar `NEEDS_MORE_EVIDENCE` e apontar quais fontes faltam, sem preencher a lista com ideias fracas.

## Red team obrigatorio

Antes de recomendar investimento, perguntar:

- O comprador e claro?
- A dor e urgente ou so curiosidade?
- A entrega minima pode ser digital e simples?
- A promessa cabe em um anuncio?
- O canal Meta Ads faz sentido?
- O score vem de pelo menos 3 familias de evidencia?
- Existe risco juridico, regulatorio, suporte pesado ou promessa impossivel?

## Arquivos uteis

- `COMO_USAR.md`: guia do usuario.
- `prompts/researcher_system_prompt.md`: prompt mestre.
- `agent.config.json`: pesos, thresholds e regras de descarte.
- `schemas/opportunity_signal.schema.json`: formato esperado das seeds.
- `opportunity_researcher/`: pacote Python.
