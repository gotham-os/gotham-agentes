from __future__ import annotations

from typing import Any

from ..utils import score_text


def _link(label: str, url: str) -> str:
    return f"[{label}]({url})" if url else label


def _render_evidence(evidence: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for item in evidence[:8]:
        metrics = f" | metrics: `{item['metrics']}`" if item.get("metrics") else ""
        quality = ""
        if item.get("metrics"):
            quality = (
                f" | qualidade: `{item['metrics'].get('quality_verdict', 'n/a')}`"
                f"/`{item['metrics'].get('quality_score', 'n/a')}`"
            )
        rows.append(
            f"- {item.get('type')}/{item.get('strength')}: "
            f"{_link(item.get('title', ''), item.get('url', ''))} "
            f"({item.get('source')}){quality}{metrics}"
        )
    return "\n".join(rows) if rows else "- Sem evidencias anexadas"


def _render_scale_proofs(evidence: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for item in evidence:
        metrics = item.get("metrics") or {}
        examples = [
            *(metrics.get("global_duplicate_examples") or []),
            *(metrics.get("duplicate_examples") or []),
        ]
        if not examples:
            continue
        rows.append(
            "- {query}: escala `{scale}` | global `{global_scale}` | cross-source `{cross}` | cross-domain `{domain}` | global cross-domain `{global_domain}` | max variantes `{variants}`".format(
                query=metrics.get("query") or item.get("title", "Meta Ads"),
                scale=metrics.get("scale_signal", "unknown"),
                global_scale=metrics.get("global_scale_signal", "none"),
                cross=metrics.get("cross_source_duplicate_groups", 0),
                domain=metrics.get("cross_domain_duplicate_groups", 0),
                global_domain=metrics.get("global_cross_domain_duplicate_groups", 0),
                variants=metrics.get("max_duplicate_variants", 1),
            )
        )
        for example in examples[:3]:
            pages = ", ".join(example.get("source_pages") or [example.get("page_name", "")])
            domains = ", ".join(example.get("destination_domains") or [])
            ids = ", ".join(example.get("library_ids") or [example.get("library_id", "")])
            queries = ", ".join(example.get("queries") or [])
            proof = example.get("proof") or example.get("type", "duplicate proof")
            rows.append(
                f"  - Prova: {example.get('type', 'duplicate')} | paginas: {pages or 'n/a'} | dominios: {domains or 'n/a'} | queries: {queries or 'n/a'} | IDs: {ids or 'n/a'} | {proof}"
            )
    return "\n".join(rows) if rows else "- Nenhum duplicado escalado detectado nesta rodada."


def _render_list(items: list[str], fallback: str = "- Ainda nao definido") -> str:
    return "\n".join(f"- {item}" for item in items) if items else fallback


def _render_opportunity(opportunity: dict[str, Any], index: int) -> str:
    scores = opportunity["scores"]
    test = opportunity.get("meta_ads_test", {})

    return f"""## {index + 1}. {opportunity["title"]}

**Decisao:** {scores["decision"]}  
**Score geral:** {score_text(scores["overall"])} | Market {score_text(scores["market"])} | Dor {score_text(scores["pain"])} | Distribuicao {score_text(scores["distribution"])} | MVP {score_text(scores["mvp"])} | Confianca {score_text(scores["confidence"])} | Meta Ads fit {score_text(scores["meta_ads_fit"])}
**Qualidade:** Evidencia {score_text(scores.get("evidence_quality", 0))} | Fontes {score_text(scores.get("source_quality", 0))} | Densidade de provas {score_text(scores.get("proof_density", 0))}

**Tipo de oferta:** {opportunity.get("offer_type") or opportunity.get("solution_type")}  
**Publico comprador:** {opportunity.get("audience")}  
**Promessa:** {opportunity.get("promise")}

**Por que agora:** {opportunity.get("why_now") or "Sinais suficientes para investigacao; precisa validar com teste controlado."}

**Evidencias**
{_render_evidence(opportunity.get("evidence", []))}

**Provas de anuncio escalado/duplicado**
{_render_scale_proofs(opportunity.get("evidence", []))}

**MVP minimo**
{_render_list(opportunity.get("mvp", []))}

**Teste Meta Ads**
- Budget: {test.get("budget", "R$300-R$700")}
- Criativos: {test.get("creatives", 4)}
- Objetivo: {test.get("objective", "Leads ou compra")}
- Matar se: {test.get("kill_rule", "Sem leads qualificados depois do gasto minimo")}
- Continuar se: {test.get("scale_rule", "Leads baratos ou primeira venda")}

**Red team**
{_render_list(opportunity.get("red_team", []), "- Sem red team cadastrado; adicionar antes de investir verba.")}

**Proximas acoes**
{_render_list(opportunity.get("next_actions", []), "- Montar landing, criativos e oferta manual antes de construir produto completo.")}
"""


def render_markdown_report(result: dict[str, Any]) -> str:
    ranking = "\n".join(
        "| {idx} | {decision} | {title} | {overall} | {market} | {mvp} | {confidence} |".format(
            idx=index + 1,
            decision=opportunity["scores"]["decision"],
            title=opportunity["title"],
            overall=score_text(opportunity["scores"]["overall"]),
            market=score_text(opportunity["scores"]["market"]),
            mvp=score_text(opportunity["scores"]["mvp"]),
            confidence=score_text(opportunity["scores"]["confidence"]),
        )
        for index, opportunity in enumerate(result.get("opportunities", []))
    )
    body = "\n---\n\n".join(
        _render_opportunity(opportunity, index)
        for index, opportunity in enumerate(result.get("opportunities", []))
    )

    return f"""# Gotham Opportunity Researcher - Relatorio

Gerado em: {result["generated_at"]}  
Run: {result["run_name"]}  
Sinais analisados: {result["signal_count"]}  
Fontes unicas: {result["source_count"]}  
Oportunidades encontradas: {result["opportunity_count"]}  
Oportunidades retornadas: {result.get("returned_opportunity_count", result["opportunity_count"])}  
Promissoras: {result.get("promising_count", 0)}/{result.get("min_promising_target", 5)}  
Status da rodada: {result.get("round_status", "UNKNOWN")}

> Nota: este agente nao promete certeza. Ele prioriza apostas por evidencia, confianca e velocidade de teste. A prova final e venda, lead qualificado ou pre-venda.

> {result.get("round_note", "")}

## Ranking

| # | Decisao | Oportunidade | Geral | Market | MVP | Confianca |
|---|---|---|---:|---:|---:|---:|
{ranking}

{body}
"""
