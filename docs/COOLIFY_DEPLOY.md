# Deploy no Coolify (Oracle ARM 4/24 — 152.67.44.141)

## Pré-requisitos

- Coolify instalado e acessível no servidor
- Repositório `gotham-agentes` na org `gotham-os` do GitHub
- Acesso SSH: `ssh -i ~/.ssh/gotham_oracle.key ubuntu@152.67.44.141`

---

## Serviços a criar no Coolify

Criar **3 serviços** separados no mesmo projeto `GOTHAM-Agentes`:

### 1. gotham-brain (FastAPI AgentOS)

| Campo | Valor |
|-------|-------|
| Tipo | Docker Compose / Dockerfile |
| Repo | `gotham-os/gotham-agentes` |
| Branch | `main` |
| Build Context | `./brain` |
| Dockerfile | `./brain/Dockerfile` |
| Porta | `8000` |
| Domínio | `brain.SEU_DOMINIO.com` (ou IP:8000) |

**Variáveis de ambiente (Secrets):**
```
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
TAVILY_API_KEY=...
GOTHAM_DB_PATH=/data/gotham_memory.db
```

**Volume:**
```
gotham-brain-data:/data
```

---

### 2. gotham-ui (Next.js)

| Campo | Valor |
|-------|-------|
| Tipo | Dockerfile |
| Repo | `gotham-os/gotham-agentes` |
| Branch | `main` |
| Build Context | `./ui` |
| Dockerfile | `./ui/Dockerfile` |
| Porta | `3000` |
| Domínio | `agents.SEU_DOMINIO.com` (ou IP:3000) |

**Build Args:**
```
NEXT_PUBLIC_AGNO_API_URL=https://brain.SEU_DOMINIO.com
```

---

### 3. gotham-roteador (Manifest LLM Router)

O `gotham-roteador` tem seu próprio `docker-compose.yml` em `GOTHAM_REPOS/gotham-roteador/`.

| Campo | Valor |
|-------|-------|
| Tipo | Docker Compose |
| Repo | `gotham-os/gotham-roteador` |
| Branch | `main` |
| Porta | `2099` |
| Domínio | `roteador.SEU_DOMINIO.com` (ou IP:2099) |

Após subir o Manifest:
1. Acesse `http://IP:2099`
2. Crie conta admin
3. Configure os providers (Anthropic, Groq, OpenAI)
4. Pegue a API key do Manifest e coloque em `brain/.env`:
   ```
   MANIFEST_BASE_URL=https://roteador.SEU_DOMINIO.com/v1
   MANIFEST_API_KEY=...
   ```

---

## Ordem de deploy

1. `gotham-roteador` primeiro (providers de LLM)
2. `gotham-brain` (depende de keys configuradas)
3. `gotham-ui` (depende do brain estar UP)

---

## Verificar se está funcionando

```bash
# brain health
curl https://brain.SEU_DOMINIO.com/v1/playground/agents

# ui
curl -I https://agents.SEU_DOMINIO.com

# roteador
curl https://roteador.SEU_DOMINIO.com/api/health
```

---

## DNS (se tiver domínio)

Apontar no seu DNS:
- `brain.` → A record → 152.67.44.141
- `agents.` → A record → 152.67.44.141  
- `roteador.` → A record → 152.67.44.141

Coolify gerencia SSL automaticamente (Let's Encrypt).
