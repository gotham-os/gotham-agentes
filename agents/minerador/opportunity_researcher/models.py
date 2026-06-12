from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Signal:
    id: str
    cluster_key: str
    source: str
    source_url: str
    captured_at: str
    region: str
    evidence_type: str
    strength: str
    title: str
    summary: str = ""
    audience: str = ""
    market: str = ""
    pain_terms: list[str] = field(default_factory=list)
    offer_terms: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Scores:
    overall: int
    market: int
    pain: int
    distribution: int
    mvp: int
    confidence: int
    meta_ads_fit: int
    evidence_quality: int
    source_quality: int
    proof_density: int
    decision: str


@dataclass(slots=True)
class Opportunity:
    cluster_key: str
    title: str
    solution_type: str
    offer_type: str
    audience: str
    promise: str
    why_now: str
    mvp: list[str]
    mvp_hours: int
    delivery_manual_possible: bool
    meta_ads_test: dict[str, Any]
    red_team: list[str]
    next_actions: list[str]
    flags: list[str]
    tags: list[str]
    pain_terms: list[str]
    offer_terms: list[str]
    scores: Scores
    evidence: list[dict[str, Any]]
