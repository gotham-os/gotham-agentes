# Scoring Formulas — Bruce Wayne (CEO/Garimpador)

> Fórmulas calibradas migradas de gotham-brainstorm/scoring.py em 2026-06-13.
> O `calculate_opportunity_score` tool implementa estas fórmulas em Python (determinístico).
> Este arquivo é a documentação legível — a fonte da verdade é `brain/lib/scoring.py`.

## Pesos de strength (qualidade da evidência)

| Strength | Multiplicador |
|---|---|
| `low` | 0.45 — anedota, post único |
| `medium` | 0.72 — padrão em múltiplos posts |
| `high` | 1.0 — dados quantitativos, múltiplas fontes |
| `verified` | 1.0 — compra confirmada, campanha ativa visível |

## Dimensões do score (0-100 cada)

### Market score
```
best_per_type = max((source_tier / 10) * strength_weight) por evidence_type
market = min(100, sum(best_per_type.values()) * 1.2)
```
Mede breadth de evidência + qualidade das fontes. Premia diversidade de tipos de evidência.

### Pain score
```
pain = min(100, count(pain_signals) * 25 + sum(relevant_count) * 2)
```
Mede urgência da dor. 4 posts de dor fortes = 100. Sem evidência de dor = 0.

### Distribution score
```
per_signal = strength_weight * (20 + min(30, relevant_count * 3))
distribution = min(100, sum(per_signal))
```
Mede prova de gasto. 1 sinal forte de Meta Ads com 15 anunciantes relevantes = ~50pts.

### MVP score
```
base = 55
+ 12 se can_deliver_manually
+ 17 se mvp_hours <= 24
+ 12 se mvp_hours <= 72
+ 4  se mvp_hours <= 120
- 18 se mvp_hours > 120
= 0  se not is_digital
+ bônus por solution_type (audit/template/ebook = +10, automation = +8, saas = +2)
```
Mede velocidade de validação. Pode testar em 72h com entrega manual = score alto.

### Confidence score
```
confidence = min(100,
    len(evidence_types) * 13  +  # diversidade de famílias
    len(sources) * 7           +  # diversidade de fontes
    count(has_url) * 3         +  # auditabilidade
    count(strength=high/verified) * 4  # força das evidências
)
```

### Meta Ads fit
```
base = 45
+ 25 se tem distribution evidence
+ 10 se solution_type em {audit, template, ebook, productized_service}
```

## Overall score (ponderado)

```
overall = (
    market       * 0.25  +
    pain         * 0.12  +
    distribution * 0.12  +
    mvp          * 0.13  +
    confidence   * 0.10  +
    meta_ads_fit * 0.06  +
    market       * 0.14  +  # proxy evidence quality
    confidence   * 0.08     # proxy proof density
)
```

**Score máximo real: ~100 (normalizado)**

## Tabela de decisão

| Overall | Condições extras | Decisão |
|---|---|---|
| ≥ 72 | + has_pain + has_distribution + has_market + ≥3 famílias | **TESTAR AGORA** |
| ≥ 55 | + ≥2 famílias de evidência | **DEEPDIVE** |
| ≥ 38 | — | **RADAR** |
| < 38 | — | **DESCARTAR** |

## Kill/Scale rules (após teste)

| Condição | Ação |
|---|---|
| Gastar R$300 sem venda | Mata |
| CTR < 1% em 48h | Mata criativo, não a oferta |
| CPC > R$3,00 em audiência fria | Revê posicionamento |
| 1 venda antes de R$300 | Continua, dobra budget |
| ROAS ≥ 2x com R$300 | Sobe para R$1.000 |
| ROAS ≥ 2x com R$1.000 | Sobe para R$5.000 |
