# gotham-agentes

Plataforma pessoal de agentes de IA do GOTHAM OS. Chat + agentes especializados com memória persistente, deep research e acesso a browser — orquestrados pelo Felipe Murdock.

---

## Arquitetura

```
gotham-agentes/
├── brain/          → Servidor FastAPI + Agno AgentOS (porta 8000)
│   ├── agents/
│   │   ├── alfred.py   → 🎩 Alfred Pennyworth (COO) — orquestrador, conselheiro estratégico
│   │   ├── ras.py      → ♟️ Ra's al Ghul (CLO) — pesquisa profunda, intel de mercado
│   │   ├── selina.py   → 💎 Selina Kyle (CMO) — copy de resposta direta (BR/ES/EN)
│   │   └── bruce.py    → 🏛️ Bruce Wayne (CEO) — garimpador de oportunidades escaladas
│   ├── lib/
│   │   └── models.py   → factory de modelo por Diretor — ManifestChat (httpx direto) ou Groq fallback
│   ├── main.py         → App FastAPI (AgentOS + CORS override)
│   ├── Dockerfile
│   └── pyproject.toml
│
├── ui/             → Chat interface Next.js (porta 3000)
│   ├── src/        → Componentes React, hooks, API client
│   ├── Dockerfile
│   └── next.config.ts
│
├── agents/
│   └── minerador/  → CLI standalone do minerador (legado Codex — base histórica do bruce_agent)
│
├── docs/
│   └── COOLIFY_DEPLOY.md  → guia passo a passo de deploy no Oracle ARM
│
└── docker-compose.yml     → orquestra brain + ui juntos
```

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Agente Runtime | [Agno v2.6.14+](https://docs.agno.com) — AgentOS/FastAPI |
| LLM padrão | Groq (Llama-3.3-70b-versatile / Qwen-qwq-32b) |
| LLM Router | [Manifest](https://manifest.build) via gotham-roteador — controle de custos + fallback |
| Chat UI | Next.js 15 + Tailwind + shadcn/ui (template oficial Agno) |
| Memória | SQLite local (por agente, persistente via Docker volume) |
| Deep Research | Tavily + DuckDuckGo tools (nativas Agno) |
| Browser | gotham-browser MCP (Playwright) — acesso a Meta Ads Library |
| Infraestrutura | Oracle ARM 4/24 (152.67.44.141) + Coolify |

---

## Agentes disponíveis

### 🎩 Alfred Pennyworth (`/alfred`)
COO e orquestrador central. Responde em PT-BR. Roteia para os especialistas (Ra's, Selina, Bruce) quando necessário. Usa Tavily para pesquisa. Memória de sessão.

### ♟️ Ra's al Ghul (`/ras`)
CLO (Chief Learning Officer). Pesquisa focada em dados verificáveis. Usa tabelas. Cita fontes. Modelo Qwen-qwq-32b (melhor custo/benefício para análise profunda).

### 💎 Selina Kyle (`/selina`)
CMO (Chief Marketing Officer). Copy de resposta direta para tráfego pago. Sabe BR, ES (hispânico), EN. Faz headlines, hooks, VSL, quiz, anúncios.

### 🏛️ Bruce Wayne (`/bruce`)
CEO. Garimpador de oportunidades digitais escaladas em BR, ES e EN.

**Fontes integradas:**
- **Meta Ads Library** — quem está gastando e o quê (via browser MCP para login)
- **TikTok Creative Center** — hashtags e anúncios em alta
- **Reddit** — dores reais de consumidores em subreddits
- **Google Trends** — tendências (geo=BR|US|ES|MX)
- **ReclameAqui** — dores do mercado BR
- **Tavily** — deep research web (fontes verificadas)
- **DuckDuckGo** — backup sem bloqueio

**Output:** JSON estruturado com score, decisão (TESTAR AGORA / DEEPDIVE / RADAR / DESCARTAR), evidências linkadas, MVP, teste Meta Ads e red team.

---

## Em produção

- **brain:** `https://brain.bmilimitada.com`
- **UI:** `https://agents.bmilimitada.com`
- **Deploy:** Coolify (app `gotham-agentes`, projeto GOTHAM-Agentes), Oracle ARM 4/24 — autodeploy via webhook GitHub no push em `main`
- **LLM:** cada Diretor (Alfred/Ra's/Selina/Bruce) usa `ManifestChat` (`brain/lib/models.py`) — GPT-5.5 via `gotham-roteador` com chave própria por agente (`MANIFEST_KEY_<DIRETOR>`); sem chave configurada cai para Groq

Rotas Agno v2.6.14+:
```
GET  /agents                       → lista agentes
GET  /agents/{id}/runs             → histórico de runs
POST /agents/{id}/runs             → chat / run
GET  /health                       → healthcheck
```

> Agno 2.6.14 breaking change: rotas mudaram de `/v1/playground/agents` para `/agents`. A UI já usa o formato novo.

---

## Deploy no Coolify

Um único app Coolify (`gotham-agentes`, build pack `dockercompose`, `docker_compose_location: /docker-compose.yml`) sobe `brain` + `ui` juntos, no projeto **GOTHAM-Agentes**. Env vars (Manifest keys, Groq, Tavily, etc.) são gerenciadas direto no Coolify e injetadas via `${VAR}` no compose — não existe `.env` commitado. Push em `main` aciona autodeploy via webhook do GitHub App `coolify-gotham-os`.

Para detalhes (provisionamento inicial, troubleshooting), ver `docs/COOLIFY_DEPLOY.md`.

---

## Como rodar local

```bash
# 1. Copiar .env
cp brain/.env.example brain/.env
# Editar brain/.env com suas chaves (GROQ_API_KEY obrigatória)

# 2. Subir stack
docker compose up --build

# 3. Acessar
# UI: http://localhost:3000
# Brain API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

---

## Como rodar brain em desenvolvimento (sem Docker)

```bash
cd brain
uv pip install -e .          # instala dependências
uvicorn main:app --reload    # servidor com hot reload
```

---

## LLM Router (Manifest / gotham-roteador)

O `gotham-roteador` roda o [Manifest](https://manifest.build) — roteador inteligente que:
- Distribui queries entre providers (Anthropic, Groq, OpenAI) por complexidade
- Controla gastos com limites por modelo
- Faz fallback automático quando um provider falha

Para ativar: após subir o Manifest, coloque `MANIFEST_BASE_URL` e `MANIFEST_API_KEY` no `brain/.env`.

---

## Browser (gotham-browser MCP)

O `gotham-browser` é um servidor MCP que expõe Playwright para os agentes. Necessário para:
- Scraping da Meta Ads Library com login
- Acesso a páginas que bloqueiam bots
- Screenshots para análise de criativos

Repo: `GOTHAM_REPOS/gotham-browser`  
Porta padrão: `3100`  
Configurar `GOTHAM_BROWSER_URL=http://gotham-browser:3100` no `brain/.env`.

---

## Adicionar novos agentes

1. Criar `brain/agents/novo_agente.py` com `Agent(...)` do Agno
2. Exportar em `brain/agents/__init__.py`
3. Adicionar na lista em `brain/main.py`
4. Redeploy

Exemplos de agentes futuros:
- `virilidade_es.py` — agente do nicho saúde masculina (mercado ES)
- `trafego.py` — otimizador de campanhas Meta/TikTok
- `seo.py` — pesquisa de palavras-chave + competitor analysis

---

## Integração com Claude Code (terminal)

```bash
# Via API direta (Agno v2.6.14+ usa /agents, não /v1/playground/agents)
curl -X POST https://brain.bmilimitada.com/agents/bruce/runs \
  -H "Content-Type: application/json" \
  -d '{"message": "Mine ofertas escaladas em saúde masculina BR e ES"}'
```

---

*GOTHAM OS — "A verdade não pertence ao Claude. A verdade vive no GOTHAM."*
