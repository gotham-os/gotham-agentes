# Deploy no Coolify (Oracle ARM 4/24 — 152.67.44.141)

## Pré-requisitos

- Coolify instalado e acessível no servidor (`https://coolify.useorcafacil.com`)
- Repositório `gotham-os/gotham-agentes` no GitHub, conectado via GitHub App `coolify-gotham-os`
- `gotham-roteador` (Manifest) já rodando em `roteador.bmilimitada.com` com agentes/keys configurados por Diretor

---

## Setup atual

Um único app Coolify gerencia `brain` + `ui` juntos:

| Campo | Valor |
|-------|-------|
| Projeto | `GOTHAM-Agentes` |
| App | `gotham-agentes` |
| Build pack | `dockercompose` |
| Compose location | `/docker-compose.yml` |
| Repo | `gotham-os/gotham-agentes` |
| Branch | `main` |
| Domínios | `brain.bmilimitada.com` (serviço `brain`, porta 8000) · `agents.bmilimitada.com` (serviço `ui`, porta 3000) |

Domínios e roteamento são definidos via labels Traefik dentro do próprio `docker-compose.yml` (não na UI do Coolify).

**Variáveis de ambiente** — configuradas em Coolify (app → Environment Variables), NÃO em `brain/.env` (não existe `.env` commitado nem em produção):

```
MANIFEST_BASE_URL=https://roteador.bmilimitada.com/v1
MANIFEST_KEY_ALFRED=mnfst_...
MANIFEST_KEY_RAS=mnfst_...
MANIFEST_KEY_SELINA=mnfst_...
MANIFEST_KEY_BRUCE=mnfst_...
GROQ_API_KEY=...        # fallback quando MANIFEST_KEY_<DIRETOR> não está setada
TAVILY_API_KEY=...
AGNO_API_KEY=...
CORS_ORIGINS=https://agents.bmilimitada.com
BRAIN_PUBLIC_URL=https://brain.bmilimitada.com   # usado como build-arg do ui
```

O `docker-compose.yml` injeta essas vars no serviço `brain` via `${VAR}` — o Coolify gera o `.env` correspondente no diretório de build automaticamente a partir do que está cadastrado no app.

**Volume:** `brain-data:/data` (persistência do SQLite `gotham_memory.db`).

---

## Autodeploy

Push em `main` → webhook do GitHub App `coolify-gotham-os` → Coolify rebuilda e redeploya `gotham-agentes` automaticamente. Sem GitHub Actions, sem deploy manual via SSH.

---

## Verificar se está funcionando

```bash
curl https://brain.bmilimitada.com/health
curl https://brain.bmilimitada.com/agents
curl -I https://agents.bmilimitada.com
```

---

## gotham-roteador (Manifest)

Roda separado, em `roteador.bmilimitada.com`. Cada Diretor (Alfred/Ra's/Selina/Bruce) tem seu próprio Agent configurado no dashboard do Manifest com primary model + fallback chain. A chave correspondente vai em `MANIFEST_KEY_<DIRETOR>` no app `gotham-agentes`.
