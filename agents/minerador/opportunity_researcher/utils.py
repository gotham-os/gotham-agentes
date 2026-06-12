from __future__ import annotations

import re
import unicodedata
from statistics import mean
from typing import Any, Iterable


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    if value != value:
        return minimum
    return max(minimum, min(maximum, value))


def as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    return [value]


def unique(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def slugify(value: str, max_len: int = 80) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug[:max_len] or "untitled"


def title_case(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("-", " ")).strip().title()


def avg(values: Iterable[float]) -> float:
    numeric = [float(value) for value in values if isinstance(value, int | float)]
    return mean(numeric) if numeric else 0.0


def score_text(value: float) -> str:
    return str(round(clamp(value))).rjust(2, "0")
