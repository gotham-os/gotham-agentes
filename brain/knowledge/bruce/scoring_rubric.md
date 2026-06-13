# Rubrica de Scoring — Bruce Wayne (CEO / Garimpador)

## Schema de evidência (tipos + força)

**evidence_type** (classificar cada sinal coletado):
| Tipo | O que é |
|---|---|
| `revenue` | Prova de receita: TrustMRR, Acquire, Flippa, AppSumo, marketplace |
| `pain` | Dor real: Reddit, X, G2, Capterra, ReclameAqui, Trustpilot, reviews |
| `distribution` | Prova de gasto: Meta Ads Library, TikTok CC, Google Ads, SimilarWeb |
| `demand` | Interesse orgânico: Google Trends, Keyword Planner, YouTube, Product Hunt |
| `trend` | Tendência emergente sem prova de receita ainda |
| `competitor` | Análise de concorrente existente |
| `gap` | Existe lá fora mas falta versão BR/LATAM ou versão simples |
| `benchmark` | Referência de mercado para comparação |

**strength** (força da evidência):
- `low` → anedota, post único, opinião
- `medium` → padrão em múltiplos posts, tendência clara
- `high` → dados quantitativos, múltiplas fontes independentes
- `verified` → compra confirmada, campanha ativa com escala visível

---

## Scoring multi-dimensional (0–10 cada)

| Dimensão | Peso | O que avalia |
|---|---|---|
| `market` | x3 | Tamanho e maturidade do mercado |
| `pain` | x3 | Urgência e especificidade da dor |
| `distribution` | x3 | Prova de gasto em ads (quem está escalando) |
| `mvp` | x2 | Velocidade de validação (pode testar em 72h com R$300-R$700?) |
| `meta_ads_fit` | x2 | Adequação ao canal Meta Ads |
| `confidence` | x1 | Confiança na evidência coletada |

**Score máximo: 140 pontos**

## Classificação

| Score | Decisão | Ação |
|---|---|---|
| 100–140 | TESTAR AGORA | Budget R$300–R$700, prazo 72h |
| 65–99 | DEEPDIVE | Ra's pesquisa mais antes de testar |
| 30–64 | RADAR | Monitorar sem ação imediata |
| 0–29 | DESCARTAR | Próxima oportunidade |

---

## Output obrigatório por oportunidade

```json
{
  "title": "Nome da oportunidade",
  "mercados": ["BR", "ES", "EN"],
  "offer_type": "auditoria | template | micro_saas | ebook | automacao | curso | newsletter | api | servico_productizado",
  "decision": "TESTAR AGORA | DEEPDIVE | RADAR | DESCARTAR",
  "scores": {
    "overall": 0,
    "market": 0,
    "pain": 0,
    "distribution": 0,
    "mvp": 0,
    "meta_ads_fit": 0,
    "confidence": 0
  },
  "comprador": "quem compra — específico",
  "dor": "dor urgente e específica",
  "promessa": "promessa testável em 1 frase",
  "evidencias": [
    {"tipo": "pain|distribution|revenue|demand|gap", "forca": "low|medium|high|verified", "fonte": "url", "resumo": "..."}
  ],
  "mvp": ["máximo 3 entregáveis para validar"],
  "meta_ads_test": {
    "budget": "R$300–R$700",
    "criativos": 4,
    "kill_rule": "quando parar",
    "scale_rule": "quando dobrar"
  },
  "red_team": ["por que a tese pode estar errada"]
}
```

---

## Regras de atuação (do minerador original)

1. Aceite qualquer formato digital escalável: SaaS, micro-SaaS, automação, template, ebook, curso, comunidade, newsletter, API, serviço productizado.
2. **Rejeite:** produtos físicos, estoque, logística, operação presencial.
3. Separe evidências de opiniões. Toda recomendação precisa ter fonte, data e tipo de evidência.
4. Não confunda hype com oportunidade. Trend só importa ligada a dor + comprador + promessa + teste.
5. **Prefira entrega manual digital antes de construir software.** Venda a dor primeiro, automatize depois.
6. Sempre red team: por que a tese pode estar errada?
7. Sempre defina critério de matar e critério de escalar.

## Kill/Scale rules padrão

- Gastar R$300 sem nenhuma venda → mata
- CTR < 1% em 48h → mata o criativo, não necessariamente a oferta
- CPC > R$3,00 em audiência fria → revê posicionamento
- 1 venda antes de R$300 → continua e dobra budget
- ROAS ≥ 2x com R$300 → sobe para R$1.000
- ROAS ≥ 2x com R$1.000 → sobe para R$5.000

## Frase-guia

> "Não pergunte: 'essa ideia é interessante?'. Pergunte: 'isso merece 72h de execução e R$300–R$1.000 de teste?'"
