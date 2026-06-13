"""
Scoring engine calibrado — Bruce Wayne (CEO/Garimpador).
Migrado de gotham-brainstorm/scoring.py em 2026-06-13.

Mantém determinismo: LLM coleta evidências, este módulo calcula o score.
"""
from __future__ import annotations

from typing import Any

# Tier de qualidade por fonte (escala 0-100)
# Hierarquia: provas de receita > dados pagos > plataformas > comunidade > manual
SOURCE_TIERS: dict[str, int] = {
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
    "meta ads library": 72,
    "google trends": 68,
    "tiktok creative center": 66,
    "product hunt": 62,
    "reclameaqui": 60,
    "reddit": 58,
    "hacker news": 55,
    "duckduckgo": 45,
    "tavily": 50,
    "manual": 30,
}

STRENGTH_WEIGHT: dict[str, float] = {
    "low": 0.45,
    "medium": 0.72,
    "high": 1.0,
    "verified": 1.0,
}

MVP_TYPE_BONUS: dict[str, float] = {
    "audit": 10, "template": 10, "ebook": 10, "productized_service": 10,
    "newsletter": 10, "automation": 8, "api": 6, "micro_saas": 4, "saas": 2,
}


def _source_tier(source: str) -> int:
    text = source.lower()
    for needle, score in SOURCE_TIERS.items():
        if needle in text:
            return score
    return 45


def _signal_quality(source: str, has_url: bool, strength: str, has_metrics: bool) -> float:
    tier = _source_tier(source)
    score = tier * 0.45
    score += 6 if has_url else -12
    score += 14 if has_metrics else -8
    if strength in {"high", "verified"}:
        score += 8
    elif strength == "low":
        score -= 8
    return max(0.0, min(100.0, score))


def _is_usable(quality: float) -> bool:
    """
    Sinal só conta no score se quality >= 50 (gate anti-ruído).

    Calibração: com multiplier 0.45 e bônus máximo +28, o gate antigo (62)
    exigia tier >= 76 (TrustMRR/Acquire/Stripe/G2/AppSumo) — fontes para as
    quais Bruce não tem nenhuma tool. Isso zerava distribution/confidence
    sempre, mesmo com evidência real da Meta Ads Library (tier 72, máximo
    teórico 60.4). Com 50, qualquer fonte tier >= 49 com URL + métricas +
    strength alto/verificado (Meta Ads, TikTok, Trends, ReclameAqui, Reddit,
    Tavily) passa — ruído sem URL/métricas continua filtrado.
    """
    return quality >= 50.0


def score_opportunity(data: dict[str, Any]) -> dict[str, Any]:
    """
    Calcula score multi-dimensional de uma oportunidade.

    Input (dict):
        title: str
        signals: list[dict] — cada sinal:
            source: str       # "meta ads library" | "reddit" | "google trends" | etc
            evidence_type: str  # revenue|pain|distribution|demand|trend|competitor|gap
            strength: str     # low|medium|high|verified
            has_url: bool     # tem link auditável?
            has_metrics: bool # tem dados numéricos (contagem, MRR, score)?
            relevant_count: int  # itens relevantes encontrados (anúncios, posts, etc.)
            notes: str        # resumo do que foi encontrado
        can_deliver_manually: bool  # pode entregar sem build de software?
        mvp_hours: int        # horas para montar MVP
        is_digital: bool      # é produto digital escalável?
        solution_type: str    # "audit"|"template"|"ebook"|"automation"|"micro_saas"|"saas"|etc

    Output (dict): scores + decision + warnings
    """
    signals = data.get("signals", [])

    enriched = []
    for s in signals:
        q = _signal_quality(
            source=s.get("source", "manual"),
            has_url=bool(s.get("has_url", False)),
            strength=s.get("strength", "medium"),
            has_metrics=bool(s.get("has_metrics", False)),
        )
        enriched.append({**s, "_quality": q, "_usable": _is_usable(q)})

    usable = [s for s in enriched if s["_usable"]]
    noise = [s for s in enriched if not s["_usable"]]

    # ── Market score ──────────────────────────────────────────────────────────
    best_by_type: dict[str, float] = {}
    for s in usable:
        w = STRENGTH_WEIGHT.get(s.get("strength", "medium"), 0.72)
        tier = _source_tier(s.get("source", "manual"))
        score = (tier / 10.0) * w
        etype = s.get("evidence_type", "benchmark")
        best_by_type[etype] = max(best_by_type.get(etype, 0.0), score)
    market = min(100.0, sum(best_by_type.values()) * 1.2)

    # ── Pain score ────────────────────────────────────────────────────────────
    pain_sigs = [s for s in usable if s.get("evidence_type") == "pain"]
    pain = min(100.0, len(pain_sigs) * 25 + sum(s.get("relevant_count", 0) for s in pain_sigs) * 2)

    # ── Distribution score ────────────────────────────────────────────────────
    dist_sigs = [s for s in usable if s.get("evidence_type") == "distribution"]
    dist = 0.0
    for s in dist_sigs:
        w = STRENGTH_WEIGHT.get(s.get("strength", "medium"), 0.72)
        relevant = s.get("relevant_count", 0)
        dist += w * (20 + min(30, relevant * 3))
    dist = min(100.0, dist)

    # ── MVP score ─────────────────────────────────────────────────────────────
    mvp = 55.0
    if data.get("can_deliver_manually", True):
        mvp += 12
    hours = data.get("mvp_hours", 72)
    if isinstance(hours, (int, float)):
        if hours <= 24:
            mvp += 17
        elif hours <= 72:
            mvp += 12
        elif hours <= 120:
            mvp += 4
        else:
            mvp -= 18
    if not data.get("is_digital", True):
        mvp = 0.0
    sol = data.get("solution_type", "productized_service").lower()
    mvp += MVP_TYPE_BONUS.get(sol, 0)
    mvp = min(100.0, max(0.0, mvp))

    # ── Confidence score ──────────────────────────────────────────────────────
    sources = list({s.get("source", "") for s in usable})
    families = list({s.get("evidence_type", "") for s in usable})
    urls = sum(1 for s in usable if s.get("has_url"))
    verified = sum(1 for s in usable if s.get("strength") in {"verified", "high"})
    confidence = min(100.0, len(families) * 13 + len(sources) * 7 + urls * 3 + verified * 4)

    # ── Meta Ads fit ──────────────────────────────────────────────────────────
    has_dist = bool(dist_sigs)
    meta_fit = 45.0 + (25 if has_dist else 0)
    if sol in {"audit", "template", "ebook", "productized_service"}:
        meta_fit += 10
    meta_fit = min(100.0, meta_fit)

    # ── Overall (pesos calibrados do brainstorm) ──────────────────────────────
    overall = (
        market * 0.25
        + pain * 0.12
        + dist * 0.12
        + mvp * 0.13
        + confidence * 0.10
        + meta_fit * 0.06
        + market * 0.14   # proxy evidence quality
        + confidence * 0.08  # proxy proof density
    )
    overall = min(100.0, max(0.0, overall))

    # ── Decision ──────────────────────────────────────────────────────────────
    has_pain_e = any(s.get("evidence_type") == "pain" for s in usable)
    has_dist_e = bool(dist_sigs)
    has_market_e = any(s.get("evidence_type") in {"revenue", "demand", "trend"} for s in usable)
    n_families = len(families)

    if overall >= 72 and has_pain_e and has_dist_e and has_market_e and n_families >= 3:
        decision = "TESTAR AGORA"
    elif overall >= 55 and n_families >= 2:
        decision = "DEEPDIVE"
    elif overall >= 38:
        decision = "RADAR"
    else:
        decision = "DESCARTAR"

    result: dict[str, Any] = {
        "title": data.get("title", "Sem título"),
        "decision": decision,
        "scores": {
            "overall": round(overall),
            "market": round(market),
            "pain": round(pain),
            "distribution": round(dist),
            "mvp": round(mvp),
            "confidence": round(confidence),
            "meta_ads_fit": round(meta_fit),
        },
        "evidence_summary": {
            "usable_signals": len(usable),
            "noise_filtered": len(noise),
            "evidence_types": list(set(s.get("evidence_type", "") for s in usable)),
            "sources": sources,
        },
    }

    if noise:
        result["warning"] = (
            f"{len(noise)} sinal(is) descartado(s) por baixa qualidade "
            f"(sources: {[s.get('source','?') for s in noise]}). "
            "Coletar evidências com URL + métricas numéricas melhora o score."
        )

    return result
