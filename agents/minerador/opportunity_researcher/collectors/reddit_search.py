from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from ..utils import slugify, unique


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "gotham-opportunity-researcher/0.1 by local-agent",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def _strength(score: int, comments: int) -> str:
    if score >= 50 or comments >= 25:
        return "high"
    if score >= 10 or comments >= 6:
        return "medium"
    return "low"


def _source_url(permalink: str) -> str:
    if permalink.startswith("http"):
        return permalink
    return f"https://www.reddit.com{permalink}"


def _summary(data: dict[str, Any]) -> str:
    text = str(data.get("selftext") or data.get("body") or "").strip()
    if text:
        return text[:700]
    return str(data.get("title") or "").strip()


def collect_reddit_search(query_config: dict[str, Any]) -> dict[str, Any]:
    captured_at = datetime.now(UTC).isoformat()
    region = query_config.get("region") or "GLOBAL"
    default_limit = int(query_config.get("limit", 8))
    default_time = query_config.get("time", "month")
    default_sort = query_config.get("sort", "relevance")
    signals: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for item in query_config.get("queries", []):
        cluster_key = item["cluster_key"]
        subreddits = item.get("subreddits") or ["all"]
        queries = item.get("queries") or [item.get("query")]
        tags = item.get("tags") or []
        limit = int(item.get("limit", default_limit))
        time_window = item.get("time", default_time)
        sort = item.get("sort", default_sort)

        for subreddit in subreddits:
            for query in [value for value in queries if value]:
                url = (
                    f"https://www.reddit.com/r/{quote(str(subreddit))}/search.json"
                    f"?q={quote(str(query))}&restrict_sr=1&sort={quote(str(sort))}"
                    f"&t={quote(str(time_window))}&limit={limit}"
                )
                try:
                    payload = _fetch_json(url)
                except Exception as error:  # noqa: BLE001 - keep collector best-effort.
                    errors.append({"subreddit": str(subreddit), "query": str(query), "error": str(error)})
                    continue

                children = payload.get("data", {}).get("children", [])
                for index, child in enumerate(children):
                    data = child.get("data", {})
                    title = str(data.get("title") or "").strip()
                    if not title:
                        continue
                    score = int(data.get("score") or 0)
                    comments = int(data.get("num_comments") or 0)
                    permalink = str(data.get("permalink") or "")
                    created = data.get("created_utc")
                    published = (
                        datetime.fromtimestamp(float(created), UTC).isoformat()
                        if isinstance(created, int | float)
                        else ""
                    )
                    signal_id = f"reddit-{slugify(cluster_key)}-{slugify(subreddit)}-{slugify(query)}-{index + 1:03d}"
                    signals.append(
                        {
                            "id": signal_id,
                            "cluster_key": cluster_key,
                            "source": f"Reddit r/{subreddit}",
                            "source_url": _source_url(permalink),
                            "captured_at": captured_at,
                            "region": region,
                            "evidence_type": item.get("evidence_type") or "pain",
                            "strength": _strength(score, comments),
                            "title": title,
                            "summary": _summary(data),
                            "audience": item.get("audience") or "Comunidade Reddit",
                            "pain_terms": unique([query, *(item.get("pain_terms") or [])]),
                            "offer_terms": item.get("offer_terms") or [],
                            "tags": unique(["reddit", "community_signal", *tags]),
                            "metrics": {
                                "subreddit": subreddit,
                                "query": query,
                                "upvotes": score,
                                "comments": comments,
                                "published": published,
                            },
                        }
                    )

    return {
        "run_name": "reddit-search",
        "captured_at": captured_at,
        "signal_count": len(signals),
        "error_count": len(errors),
        "signals": signals,
        "errors": errors,
    }
