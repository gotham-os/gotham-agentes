# gotham-agentes

Plataforma pessoal de agentes de IA do GOTHAM OS. Chat + agentes especializados com memória persistente, deep research, RAG e acesso a browser — orquestrados pelo Felipe Murdock.

---

## Arquitetura

```
gotham-agentes/
├── brain/          → Servidor FastAPI + Agno AgentOS (porta 8000)
│   ├── agents/
│   │   ├── alfred.py       → Alfred: conselheiro estratégico geral
│   │   ├── pesquisador.py  → Pesquisador: dados verificáveis + tabelas
│   │   ├── copywriter.py   → Copywriter: copy de resposta direta (BR/ES/EN)
│   │   └── minerador.py    → Minerador: garimpador de ofertas escaladas
│   ├── main.py             → App FastAPIApp (AgentOS)
│   ├── Dockerfile
│   └── pyproject.toml
│
├── ui/             → Chat interface Next.js (porta 3000)
│   ├── src/        → Componentes React, hooks, API client
│   ├── Dockerfile
│   └── next.config.ts
│
├── agents/
│   └── minerador/  → CLI standalone do minerador (legado Codex, base do agente Agno)
│       ├── opportunity_researcher/  → coletores Reddit, Google Trends, Meta Ads
│       ├── data/                    → rounds anteriores (histórico de oportunidades)
│       └── prompts/                 → system prompts calibrados
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
| Agente Runtime | [Agno v2](https://docs.agno.com) — AgentOS/FastAPI |
| LLM padrão | Groq (Llama-3.3-70b / Qwen-3-32b) |
| LLM premium | Claude Sonnet 4.6 (quando `ANTHROPIC_API_KEY` definida) |
| LLM Router | [Manifest](https://manifest.build) — controle de custos + fallback |
| Chat UI | Next.js 15 + Tailwind + shadcn/ui (template oficial Agno) |
| Memória | SQLite local (por agente, persistente via Docker volume) |
| RAG | ChromaDB + Vertex AI embeddings (gotham-rag) |
| Deep Research | Tavily + DuckDuckGo tools (nativas Agno) |
| Browser | gotham-browser MCP (Playwright) — acesso a Meta Ads Library |
| Infraestrutura | Oracle ARM 4/24 (152.67.44.141) + Coolify |

---

## Agentes disponíveis

### Alfred (`/alfred`)
Conselheiro estratégico geral. Responde em PT-BR. Usa Tavily para pesquisa quando necessário. Memória de sessão.

### Pesquisador (`/pesquisador`)
Pesquisa focada em dados verificáveis. Usa tabelas. Cita fontes. Modelo Qwen-3-32b (melhor custo/benefício para pesquisa).

### Copywriter (`/copywriter`)
Copy de resposta direta para tráfego pago. Sabe BR, ES (hispânico), EN. Faz headlines, hooks, VSL, quiz, anúncios.

### Minerador de Ofertas (`/minerador`)
⭐ Agente principal. Garimpador de ofertas escaladas em BR, ES e EN.

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

## Como rodar local

```bash
# 1. Copiar .env
cp brain/.env.example brain/.env
# Editar brain/.env com suas chaves (GROQ_API_KEY já está, adicionar ANTHROPIC se quiser)

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
- Tem painel web em `http://IP:2099`

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

## RAG (gotham-rag)

Para os agentes consumirem conhecimento do vault (transcrições, playbooks):

```bash
# Indexar documentos
python /mnt/c/GOTHAM_REPOS/gotham-rag/GOTHAM_RAG_SIMPLE.py index --source "caminho/para/docs"

# Os agentes consultam o ChromaDB automaticamente quando ativado
```

---

## Deploy no Coolify

Ver `docs/COOLIFY_DEPLOY.md` para guia completo passo a passo.

**TL;DR:**
1. Push para `gotham-os/gotham-agentes` no GitHub
2. No Coolify: criar 3 apps (brain, ui, roteador)
3. Configurar domínios e variáveis de ambiente
4. Deploy

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

Os agentes também podem ser chamados via CLI do Alfred diretamente:

```bash
# Via terminal GOTHAM (WSL)
alfred-claude   # Claude Code com contexto GOTHAM
alfred-codex    # GPT-5.5 via Codex

# Ou via API direta
curl -X POST http://localhost:8000/v1/playground/agents/minerador/runs \
  -H "Content-Type: application/json" \
  -d '{"message": "Mine ofertas escaladas em saúde masculina BR e ES"}'
```

---

## Histórico de rodadas (Minerador)

Rodadas anteriores salvas em `agents/minerador/data/`:
- `opportunities/` — resultados processados (JSON + score)
- `reports/` — relatórios HTML (kanban + war room) e Markdown
- `raw/` — dados brutos por fonte

Para abrir o último relatório:
```bash
open agents/minerador/data/reports/$(ls agents/minerador/data/reports/*.html | tail -1)
```

---

*GOTHAM OS — "A verdade não pertence ao Claude. A verdade vive no GOTHAM."*
