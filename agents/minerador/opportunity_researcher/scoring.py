from __future__ import annotations

from typing import Any

from .models import Scores, Signal
from .utils import as_list, clamp, unique


STRENGTH_MULTIPLIER = {
    "low": 0.45,
    "medium": 0.72,
    "high": 1.0,
    "verified": 1.0,
}


def _strength(signal: Signal) -> float:
    return STRENGTH_MULTIPLIER.get(signal.strength.lower(), 0.72)


def _quality(signal: Signal) -> float:
    score = signal.metrics.get("quality_score", 55)
    if isinstance(score, int | float):
        return clamp(float(score), 0, 100) / 100
    return 0.55


def _is_usable(signal: Signal) -> bool:
    return _quality(signal) >= 0.62


def _metric_bonus(signals: list[Signal], keys: list[str], cap: int) -> float:
    bonus = 0.0
    for signal in signals:
        if not _is_usable(signal):
            continue
        for key in keys:
            if signal.metrics.get(key) not in (None, ""):
                bonus += 2
    return min(cap, bonus)


def evidence_score(signals: list[Signal], config: dict[str, Any]) -> float:
    weights = config.get("market_score_weights", {})
    best_by_type: dict[str, float] = {}

    for signal in signals:
        if not _is_usable(signal):
            continue
        weight = float(weights.get(signal.evidence_type, 6))
        score = weight * _strength(signal) * (0.65 + _quality(signal) * 0.35)
        best_by_type[signal.evidence_type] = max(best_by_type.get(signal.evidence_type, 0), score)

    base = sum(best_by_type.values())
    metrics = _metric_bonus(
        signals,
        [
            "mrr",
            "revenue",
            "reviews",
            "posts",
            "ad_age_days",
            "search_volume",
            "upvotes",
            "scaled_duplicate_groups",
            "cross_source_duplicate_groups",
            "cross_domain_duplicate_groups",
            "global_duplicate_groups",
            "global_cross_query_duplicate_groups",
            "global_cross_cluster_duplicate_groups",
            "global_cross_domain_duplicate_groups",
        ],
        cap=10,
    )
    return clamp(base + metrics)


def pain_score(signals: list[Signal], hypothesis: dict[str, Any]) -> float:
    pain_signals = [signal for signal in signals if signal.evidence_type == "pain" and _is_usable(signal)]
    pain_terms = unique(
        [
            *[term for signal in signals for term in signal.pain_terms],
            *as_list(hypothesis.get("pain_terms")),
        ]
    )
    urgency_words = [
        "wasting",
        "burning",
        "perdendo",
        "queimando",
        "caro",
        "manual",
        "confusing",
        "scary",
        "zero leads",
        "sem vendas",
        "taxa",
        "imposto",
        "reembolso",
    ]
    urgency_hits = sum(
        1
        for term in pain_terms
        if any(word in term.lower() for word in urgency_words)
    )
    return clamp(len(pain_signals) * 18 + len(pain_terms) * 4 + urgency_hits * 5)


def distribution_score(signals: list[Signal], hypothesis: dict[str, Any]) -> float:
    distribution = [
        signal
        for signal in signals
        if signal.evidence_type == "distribution"
        and _is_usable(signal)
        and int(signal.metrics.get("relevant_cards", signal.metrics.get("cards_found", 0)) or 0) > 0
    ]
    demand = [signal for signal in signals if signal.evidence_type in {"demand", "trend"} and _is_usable(signal)]
    tags = {
        tag.lower()
        for tag in [
            *[tag for signal in signals for tag in signal.tags],
            *as_list(hypothesis.get("tags")),
        ]
    }
    paid_fit = bool(tags & {"meta_ads", "paid_traffic", "direct_response", "appsumo", "tiktok", "creative"})
    distribution_points = sum(
        22
        * {"low": 0.35, "medium": 0.72, "high": 1, "verified": 1}.get(signal.strength.lower(), 0.72)
        * (0.65 + _quality(signal) * 0.35)
        for signal in distribution
    )
    scale_points = 0.0
    for signal in distribution:
        scale_signal = str(signal.metrics.get("scale_signal", "")).lower()
        relevant_cards = int(signal.metrics.get("relevant_cards", signal.metrics.get("cards_found", 0)) or 0)
        relevance_rate = signal.metrics.get("relevance_rate", 1)
        if isinstance(relevance_rate, int | float) and relevance_rate < 0.5:
            scale_points -= 18
        if relevant_cards < 5:
            scale_points -= 8
        if scale_signal == "high" and relevant_cards >= 5:
            scale_points += 10
        elif scale_signal == "medium" and relevant_cards >= 3:
            scale_points += 5
        if int(signal.metrics.get("cross_source_duplicate_groups", 0) or 0) > 0:
            scale_points += 8
        if int(signal.metrics.get("cross_domain_duplicate_groups", 0) or 0) > 0:
            scale_points += 8
        global_scale_signal = str(signal.metrics.get("global_scale_signal", "")).lower()
        if global_scale_signal == "high":
            scale_points += 12
        elif global_scale_signal == "medium":
            scale_points += 6
        if int(signal.metrics.get("global_cross_query_duplicate_groups", 0) or 0) > 0:
            scale_points += 6
        if int(signal.metrics.get("global_cross_domain_duplicate_groups", 0) or 0) > 0:
            scale_points += 10

    return clamp(distribution_points + scale_points + len(demand) * 10 + (14 if paid_fit and distribution else 0))


def evidence_quality_score(signals: list[Signal]) -> float:
    if not signals:
        return 0
    return clamp(sum(int(signal.metrics.get("quality_score", 0) or 0) for signal in signals) / len(signals))


def source_quality_score(signals: list[Signal]) -> float:
    if not signals:
        return 0
    return clamp(sum(int(signal.metrics.get("source_tier", 0) or 0) for signal in signals) / len(signals))


def proof_density_score(signals: list[Signal]) -> float:
    core = [signal for signal in signals if signal.metrics.get("core_evidence")]
    sources = unique(signal.source for signal in signals if _is_usable(signal))
    families = unique(signal.evidence_type for signal in core)
    return clamp(len(core) * 16 + len(sources) * 7 + len(families) * 9)


def meta_ads_fit_score(signals: list[Signal], hypothesis: dict[str, Any]) -> float:
    explicit = hypothesis.get("meta_ads_fit")
    if isinstance(explicit, int | float):
        return clamp(float(explicit))

    tags = {
        tag.lower()
        for tag in [
            *[tag for signal in signals for tag in signal.tags],
            *as_list(hypothesis.get("tags")),
        ]
    }
    solution_type = str(hypothesis.get("solution_type", "")).lower()
    score = 45

    if tags & {"meta_ads", "paid_traffic"}:
        score += 25
    if tags & {
        "scaled_ads_signal",
        "cross_source_duplicate_ad",
        "cross_domain_duplicate_ad",
        "global_scaled_ad_signal",
        "cross_query_duplicate_ad",
        "cross_cluster_duplicate_ad",
        "global_cross_domain_duplicate_ad",
    }:
        score += 8
    if "direct_response" in tags:
        score += 12
    if tags & {"b2b", "smb", "ecommerce", "creator"}:
        score += 8
    if solution_type in {"audit", "template", "service", "productized_service", "ebook"}:
        score += 10
    if tags & {"regulated", "sensitive"}:
        score -= 18
    if "cannot_test_with_meta_ads" in as_list(hypothesis.get("flags")):
        score = 0

    return clamp(score)


def mvp_score(hypothesis: dict[str, Any], config: dict[str, Any]) -> float:
    rules = config.get("mvp_rules", {})
    solution_type = str(hypothesis.get("solution_type", "")).lower()
    flags = set(as_list(hypothesis.get("flags")))
    hours = hypothesis.get("mvp_hours")
    score = 58.0

    if hypothesis.get("delivery_manual_possible", True):
        score += float(rules.get("manual_delivery_bonus", 12))

    if isinstance(hours, int | float):
        if hours <= 24:
            score += 17
        elif hours <= 72:
            score += 12
        elif hours <= 120:
            score += 4
        else:
            score -= 18

    if solution_type in {"audit", "template", "productized_service", "ebook", "course", "spreadsheet", "data_product", "automation", "api", "newsletter", "community"}:
        score += 10
    if solution_type in {"saas", "micro_saas"}:
        score += 2
    if solution_type in {"physical_product", "ecommerce_physical"}:
        score = 0
    if "requires_api" in flags:
        score -= float(rules.get("api_dependency_penalty", 15))
    if "requires_scraping" in flags:
        score -= 8
    if "regulated_market" in flags:
        score -= float(rules.get("regulated_market_penalty", 20))
    if "needs_complex_integration" in flags:
        score -= 16
    if "no_minimum_deliverable" in flags:
        score = 0
    if {"physical_product", "physical_inventory", "offline_delivery_only"} & flags:
        score = 0

    return clamp(score)


def confidence_score(signals: list[Signal]) -> float:
    usable = [signal for signal in signals if _is_usable(signal)]
    sources = unique(signal.source for signal in usable)
    families = unique(signal.evidence_type for signal in usable)
    links = sum(1 for signal in usable if signal.source_url)
    metrics = sum(1 for signal in usable if signal.metrics)
    verified = sum(1 for signal in usable if signal.strength.lower() in {"verified", "high"})

    score = len(families) * 13 + len(sources) * 7 + links * 3 + metrics * 4 + verified * 4
    if len(usable) < 3:
        score -= 15
    if len(sources) < 2:
        score -= 10
    return clamp(score)


def has_fatal_flag(hypothesis: dict[str, Any], config: dict[str, Any]) -> bool:
    fatal_flags = set(config.get("fatal_flags", []))
    return bool(fatal_flags & set(as_list(hypothesis.get("flags"))))


def _core_counts(signals: list[Signal]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for signal in signals:
        if signal.metrics.get("core_evidence"):
            counts[signal.evidence_type] = counts.get(signal.evidence_type, 0) + 1
    return counts


def score_opportunity(signals: list[Signal], hypothesis: dict[str, Any], config: dict[str, Any]) -> Scores:
    market = evidence_score(signals, config)
    pain = pain_score(signals, hypothesis)
    distribution = distribution_score(signals, hypothesis)
    mvp = mvp_score(hypothesis, config)
    confidence = confidence_score(signals)
    meta_ads_fit = meta_ads_fit_score(signals, hypothesis)
    evidence_quality = evidence_quality_score(signals)
    source_quality = source_quality_score(signals)
    proof_density = proof_density_score(signals)

    overall = clamp(
        market * 0.25
        + pain * 0.12
        + distribution * 0.12
        + mvp * 0.13
        + confidence * 0.10
        + meta_ads_fit * 0.06
        + evidence_quality * 0.14
        + proof_density * 0.08
    )

    thresholds = config.get("decision_thresholds", {})
    decision = "DESCARTAR"
    core = _core_counts(signals)
    has_money = core.get("revenue", 0) > 0
    has_pain = core.get("pain", 0) > 0
    has_distribution = core.get("distribution", 0) > 0
    has_demand = core.get("demand", 0) > 0 or core.get("trend", 0) > 0
    has_market_proof = has_money or has_demand
    core_count = sum(core.values())

    if has_fatal_flag(hypothesis, config):
        decision = "DESCARTAR"
    elif (
        overall >= thresholds.get("test_now", 78)
        and market >= 62
        and mvp >= 65
        and confidence >= 55
        and evidence_quality >= 62
        and proof_density >= 55
        and core_count >= 3
        and has_pain
        and has_distribution
        and has_market_proof
    ):
        decision = "TESTAR AGORA"
    elif overall >= thresholds.get("deepdive", 65) and core_count >= 2 and evidence_quality >= 50:
        decision = "DEEPDIVE"
    elif overall >= thresholds.get("radar", 50):
        decision = "RADAR"

    return Scores(
        overall=round(overall),
        market=round(market),
        pain=round(pain),
        distribution=round(distribution),
        mvp=round(mvp),
        confidence=round(confidence),
        meta_ads_fit=round(meta_ads_fit),
        evidence_quality=round(evidence_quality),
        source_quality=round(source_quality),
        proof_density=round(proof_density),
        decision=decision,
    )
