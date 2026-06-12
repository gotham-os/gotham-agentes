from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .evidence_quality import enrich_signal_quality, opportunity_quality_audit
from .models import Opportunity, Signal
from .scoring import score_opportunity
from .utils import as_list, slugify, title_case, unique


def normalize_signal(raw: dict[str, Any], index: int) -> Signal:
    title = raw.get("title") or f"Signal {index + 1}"
    cluster_key = raw.get("cluster_key") or slugify(raw.get("opportunity") or raw.get("market") or title)
    return Signal(
        id=raw.get("id") or f"sig-{index + 1:03d}",
        cluster_key=cluster_key,
        source=raw.get("source") or "manual",
        source_url=raw.get("source_url") or "",
        captured_at=raw.get("captured_at") or datetime.now(UTC).isoformat(),
        region=raw.get("region") or "GLOBAL",
        evidence_type=raw.get("evidence_type") or "benchmark",
        strength=raw.get("strength") or "medium",
        title=title,
        summary=raw.get("summary") or "",
        audience=raw.get("audience") or "",
        market=raw.get("market") or "",
        pain_terms=[str(item) for item in as_list(raw.get("pain_terms"))],
        offer_terms=[str(item) for item in as_list(raw.get("offer_terms"))],
        tags=[str(item) for item in as_list(raw.get("tags"))],
        metrics=raw.get("metrics") or {},
    )


def infer_mvp(hypothesis: dict[str, Any], signals: list[Signal]) -> list[str]:
    if hypothesis.get("mvp"):
        return [str(item) for item in as_list(hypothesis["mvp"])]

    tags = {tag.lower() for signal in signals for tag in signal.tags}
    if tags & {"paid_traffic", "meta_ads"}:
        return [
            "Landing page com promessa unica",
            "Diagnostico manual ou semi-manual em ate 24h",
            "Relatorio PDF com plano de acao e proximo passo pago",
        ]

    return [
            "Landing page com promessa especifica",
            "Formulario de entrada do cliente",
            "Entrega digital manual do primeiro resultado para validar compra",
    ]


def default_meta_ads_test(hypothesis: dict[str, Any]) -> dict[str, Any]:
    return hypothesis.get("meta_ads_test") or {
        "budget": "R$300-R$700",
        "creatives": 4,
        "objective": "Leads ou vendas com checkout simples",
        "kill_rule": "Matar se nao gerar lead qualificado ou checkout iniciado apos gasto minimo definido",
        "scale_rule": "Continuar se gerar leads baratos, primeira venda ou sinais claros de intent",
    }


def summarize_evidence(signals: list[Signal]) -> list[dict[str, Any]]:
    return [
        {
            "id": signal.id,
            "type": signal.evidence_type,
            "source": signal.source,
            "strength": signal.strength,
            "title": signal.title,
            "url": signal.source_url,
            "metrics": signal.metrics,
        }
        for signal in signals
    ]


def build_hypothesis(cluster_key: str, signals: list[Signal], raw: dict[str, Any]) -> dict[str, Any]:
    first = signals[0] if signals else None
    tags = unique(
        [
            *[tag for signal in signals for tag in signal.tags],
            *as_list(raw.get("tags")),
        ]
    )
    pain_terms = unique(
        [
            *[term for signal in signals for term in signal.pain_terms],
            *as_list(raw.get("pain_terms")),
        ]
    )
    offer_terms = unique(
        [
            *[term for signal in signals for term in signal.offer_terms],
            *as_list(raw.get("offer_terms")),
        ]
    )

    return {
        "cluster_key": cluster_key,
        "title": raw.get("title") or title_case(cluster_key),
        "solution_type": raw.get("solution_type") or "productized_service",
        "offer_type": raw.get("offer_type") or raw.get("solution_type") or "productized_service",
        "audience": raw.get("audience") or (first.audience if first else "") or "Comprador ainda nao definido",
        "promise": raw.get("promise") or (first.summary if first else "") or "Promessa precisa ser refinada",
        "why_now": raw.get("why_now") or "",
        "mvp": infer_mvp(raw, signals),
        "mvp_hours": int(raw.get("mvp_hours", 72)),
        "delivery_manual_possible": bool(raw.get("delivery_manual_possible", True)),
        "meta_ads_fit": raw.get("meta_ads_fit"),
        "meta_ads_test": default_meta_ads_test(raw),
        "red_team": [str(item) for item in as_list(raw.get("red_team"))],
        "next_actions": [str(item) for item in as_list(raw.get("next_actions"))],
        "flags": [str(item) for item in as_list(raw.get("flags"))],
        "tags": tags,
        "pain_terms": pain_terms,
        "offer_terms": offer_terms,
    }


def run_opportunity_research(input_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    signals = [normalize_signal(raw, index) for index, raw in enumerate(as_list(input_data.get("signals")))]
    enrich_signal_quality(signals)
    hypothesis_by_key = {
        item["cluster_key"]: item
        for item in as_list(input_data.get("opportunity_hypotheses"))
        if isinstance(item, dict) and item.get("cluster_key")
    }

    groups: dict[str, list[Signal]] = defaultdict(list)
    for signal in signals:
        groups[signal.cluster_key].append(signal)

    opportunities: list[Opportunity] = []
    opportunity_audits: dict[str, dict[str, Any]] = {}
    for cluster_key, group_signals in groups.items():
        audit = opportunity_quality_audit(group_signals)
        opportunity_audits[cluster_key] = audit
        hypothesis = build_hypothesis(cluster_key, group_signals, hypothesis_by_key.get(cluster_key, {}))
        scores = score_opportunity(group_signals, hypothesis, config)
        opportunities.append(
            Opportunity(
                **{key: value for key, value in hypothesis.items() if key != "meta_ads_fit"},
                scores=scores,
                evidence=summarize_evidence(group_signals),
            )
        )

    opportunities.sort(key=lambda item: item.scores.overall, reverse=True)
    round_output = config.get("round_output", {})
    promising_decisions = set(round_output.get("promising_decisions", ["TESTAR AGORA", "DEEPDIVE", "RADAR"]))
    min_promising = int(round_output.get("min_promising", 5))
    max_ranked = int(round_output.get("max_ranked", 12))
    promising_count = sum(1 for item in opportunities if item.scores.decision in promising_decisions)
    output_opportunities = opportunities[:max_ranked]

    return {
        "run_name": input_data.get("run_name") or "opportunity-radar",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_count": len(unique(signal.source for signal in signals)),
        "signal_count": len(signals),
        "opportunity_count": len(opportunities),
        "returned_opportunity_count": len(output_opportunities),
        "promising_count": promising_count,
        "min_promising_target": min_promising,
        "round_status": "ENOUGH_PROMISING" if promising_count >= min_promising else "NEEDS_MORE_EVIDENCE",
        "round_note": (
            f"Rodada abaixo do alvo: {promising_count}/{min_promising} oportunidades promissoras. "
            "Coletar mais sinais antes de montar muitos MVPs."
            if promising_count < min_promising
            else f"Rodada atingiu o alvo: {promising_count}/{min_promising} oportunidades promissoras."
        ),
        "quality_summary": {
            "strong_sources": sum(1 for signal in signals if int(signal.metrics.get("quality_score", 0) or 0) >= 78),
            "weak_or_noise_sources": sum(1 for signal in signals if str(signal.metrics.get("quality_verdict")) in {"weak", "noise"}),
            "core_evidence": sum(1 for signal in signals if signal.metrics.get("core_evidence")),
        },
        "opportunities": [asdict(item) for item in output_opportunities],
        "opportunity_quality": opportunity_audits,
    }
