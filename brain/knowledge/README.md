# Knowledge Base — GOTHAM Agentes

Insumos que os agentes consomem via tool `load_*_knowledge`.
**Conteúdo definido e curado pelo Felipe Murdock — não alterar sem aprovação.**

## Estrutura

```
knowledge/
├── selina/          → 💎 CMO — copy, frameworks DRC, swipe file
│   ├── drc_framework.md       → framework Dor→Agitação→Solução
│   ├── hooks_formulas.md      → 12 fórmulas de hook
│   ├── headlines_formulas.md  → fórmulas de headline
│   ├── vsl_framework.md       → estrutura de VSL
│   └── swipe_file.md          → ⭐ PREENCHER: anúncios aprovados, depoimentos, avatares
│
├── ras/             → ♟️ CLO — frameworks de pesquisa, fontes, templates
│   ├── research_frameworks.md → OODA, hierarquia de evidência
│   ├── fontes_confiveis.md    → catálogo de fontes por tipo de dado
│   └── research_templates.md  → templates de output (nicho, concorrente)
│
├── bruce/           → 🏛️ CEO — rubrica de scoring, critérios de oportunidade
│   └── scoring_rubric.md      → critérios + kill rules + scale rules
│
└── alfred/          → 🎩 COO — protocolos de decisão (a preencher)
```

## Como adicionar insumos

1. Edite o arquivo `.md` da pasta do diretor responsável
2. O agente carrega o arquivo via tool `load_copy_knowledge` / `load_research_knowledge`
3. Sem rebuild necessário — leitura em tempo real do filesystem

## Env vars relevantes

| Var | Default | Descrição |
|---|---|---|
| `GOTHAM_KNOWLEDGE_PATH` | `./knowledge` | Raiz do knowledge base |
| `GOTHAM_OUTPUTS_PATH` | `./outputs` | Onde agentes salvam outputs |
| `GOTHAM_DB_PATH` | `./gotham_memory.db` | SQLite de memória de sessão |
