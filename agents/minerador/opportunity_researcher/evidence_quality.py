from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Signal
from .utils import as_list, clamp, unique


CORE_TYPES = {"revenue", "pain", "distribution", "demand", "competitor"}
SOURCE_TIERS = {
    "trustmrr": 95,
    "baremetrics": 92,
    "stripe": 92,
    "acquire": 88,
    "flippa": 86,
    "appsumo": 78,
    "g2": 76,
    "capterra": 76,
    "similarweb": 74,
    "semrush": 74,
    "google keyword planner": 72,
    "google trends": 68,
    "meta ads library": 72,
    "tiktok creative center": 66,
    "product hunt": 62,
    "reddit": 58,
    "hacker news": 55,
    "manual": 30,
}


@dataclass(slots=True)
class QualityAudit:
    score: int
    source_tier: int
    verdict: str
    core: bool
    problems: list[str]
    strengths: list[str]


def _source_tier(source: str) -> int:
    text = source.lower()
    for needle, score in SOURCE_TIERS.items():
        if needle in text:
            return score
    return 45


def _has_any(metrics: dict[str, Any], keys: list[str]) -> bool:
    return any(metrics.get(key) not in (None, "", [], {}) for key in keys)


def _int_metric(metrics: dict[str, Any], key: str, default: int = 0) -> int:
    value = metrics.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return default


def _float_metric(metrics: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = metrics.get(key, default)
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return default


def audit_signal_quality(signal: Signal) -> QualityAudit:
    metrics = signal.metrics or {}
    source_tier = _source_tier(signal.source)
    score = source_tier * 0.45
    problems: list[str] = []
    strengths: list[str] = []

    if signal.source_url:
        score += 6
        strengths.append("tem link auditavel")
    else:
        score -= 12
        problems.append("sem link auditavel")

    if signal.evidence_type == "revenue":
        if _has_any(metrics, ["mrr", "arr", "revenue", "price_usd", "listing_price", "reviews", "rating"]):
            score += 24
            strengths.append("tem metrica de receita/preco/reviews")
        else:
            score -= 18
            problems.append("receita sem metrica verificavel")

    if signal.evidence_type == "pain":
        if _has_any(metrics, ["upvotes", "comments", "reviews", "rating", "complaints", "posts"]):
            score += 18
            strengths.append("dor com metrica de comunidade/review")
        elif "search/?" in signal.source_url or "/search/" in signal.source_url:
            score -= 28
            problems.append("dor baseada apenas em pagina de busca, nao em posts/reviews extraidos")
        else:
            score -= 8
            problems.append("dor sem volume ou exemplos mensurados")

    if signal.evidence_type == "distribution":
        cards = _int_metric(metrics, "cards_found")
        relevant = _int_metric(metrics, "relevant_cards", cards)
        relevance_rate = _float_metric(metrics, "relevance_rate", 1.0 if cards else 0.0)
        active = _int_metric(metrics, "active_ads")
        duplicate_groups = _int_metric(metrics, "global_duplicate_groups") + _int_metric(metrics, "cross_source_duplicate_groups")
        if cards and not relevant:
            score -= 35
            problems.append("anuncios encontrados, mas nenhum relevante para a tese")
        elif cards:
            score += min(22, relevant * 3)
            strengths.append(f"{relevant}/{cards} anuncios relevantes")
        if cards and relevance_rate < 0.5:
            score -= 24
            problems.append(f"baixa precisao da query ({relevance_rate:.0%} relevante)")
        if active >= 5 and relevant >= 5:
            score += 10
            strengths.append("5+ anuncios ativos relevantes")
        if duplicate_groups:
            score += min(14, duplicate_groups * 7)
            strengths.append("duplicacao/escala detectada")

    if signal.evidence_type in {"demand", "trend"}:
        if _has_any(metrics, ["traffic_value", "search_volume", "growth", "trend_score"]):
            score += 16
            strengths.append("demanda com metrica")
        else:
            score -= 10
            problems.append("trend/demanda sem volume numerico")

    if signal.evidence_type == "competitor":
        if _has_any(metrics, ["traffic", "visits", "keywords", "mrr", "reviews", "employees"]):
            score += 16
            strengths.append("concorrente com metrica")
        else:
            score -= 8
            problems.append("concorrente sem metrica")

    if signal.strength.lower() in {"high", "verified"}:
        score += 8
    elif signal.strength.lower() == "low":
        score -= 8

    score = round(clamp(score))
    core = signal.evidence_type in CORE_TYPES and score >= 62
    if score >= 78:
        verdict = "strong"
    elif score >= 62:
        verdict = "usable"
    elif score >= 45:
        verdict = "weak"
    else:
        verdict = "noise"

    return QualityAudit(
        score=score,
        source_tier=source_tier,
        verdict=verdict,
        core=core,
        problems=unique(problems),
        strengths=unique(strengths),
    )


def enrich_signal_quality(signals: list[Signal]) -> None:
    for signal in signals:
        audit = audit_signal_quality(signal)
        signal.metrics = {
            **(signal.metrics or {}),
            "quality_score": audit.score,
            "source_tier": audit.source_tier,
            "quality_verdict": audit.verdict,
            "core_evidence": audit.core,
            "quality_problems": audit.problems,
            "quality_strengths": audit.strengths,
        }
        if audit.verdict == "noise":
            signal.tags = unique([*signal.tags, "noise_signal"])
        elif audit.verdict == "weak":
            signal.tags = unique([*signal.tags, "weak_signal"])


def opportunity_quality_audit(signals: list[Signal]) -> dict[str, Any]:
    enrich_signal_quality(signals)
    core = [signal for signal in signals if signal.metrics.get("core_evidence")]
    usable = [signal for signal in signals if int(signal.metrics.get("quality_score", 0) or 0) >= 62]
    strong = [signal for signal in signals if int(signal.metrics.get("quality_score", 0) or 0) >= 78]
    by_type = {kind: 0 for kind in CORE_TYPES}
    for signal in core:
        by_type[signal.evidence_type] = by_type.get(signal.evidence_type, 0) + 1
    sources = unique(signal.source for signal in usable)
    problems = unique(problem for signal in signals for problem in as_list(signal.metrics.get("quality_problems")))
    strengths = unique(strength for signal in signals for strength in as_list(signal.metrics.get("quality_strengths")))
    avg_quality = round(sum(int(signal.metrics.get("quality_score", 0) or 0) for signal in signals) / len(signals)) if signals else 0
    source_quality = round(sum(int(signal.metrics.get("source_tier", 0) or 0) for signal in signals) / len(signals)) if signals else 0
    proof_density = round(clamp(len(core) * 18 + len(sources) * 8 + len(strong) * 7))

    return {
        "average_quality": avg_quality,
        "source_quality": source_quality,
        "proof_density": proof_density,
        "core_evidence_count": len(core),
        "usable_evidence_count": len(usable),
        "strong_evidence_count": len(strong),
        "usable_source_count": len(sources),
        "core_by_type": by_type,
        "has_revenue_proof": by_type.get("revenue", 0) > 0,
        "has_pain_proof": by_type.get("pain", 0) > 0,
        "has_distribution_proof": by_type.get("distribution", 0) > 0,
        "has_demand_proof": by_type.get("demand", 0) > 0 or by_type.get("trend", 0) > 0,
        "problems": problems[:10],
        "strengths": strengths[:10],
    }
