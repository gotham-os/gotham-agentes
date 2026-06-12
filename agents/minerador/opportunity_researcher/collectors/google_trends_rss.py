from __future__ import annotations

from datetime import UTC, datetime
import re
from html import unescape
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ..utils import slugify


def _text(item: ElementTree.Element, name: str) -> str:
    found = item.find(name)
    return unescape(found.text or "").strip() if found is not None else ""


def _ht_text(item: ElementTree.Element, name: str) -> str:
    found = item.find(f"{{https://trends.google.com/trending/rss}}{name}")
    return unescape(found.text or "").strip() if found is not None else ""


def _traffic_value(value: str) -> int:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*([KMB]?)", value.upper())
    if not match:
        return 0
    number = float(match.group(1).replace(",", "."))
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(match.group(2), 1)
    return int(number * multiplier)


def collect_google_trends_daily(geo: str = "BR") -> dict:
    url = f"https://trends.google.com/trending/rss?geo={quote(geo)}"
    request = Request(url, headers={"User-Agent": "gotham-opportunity-researcher/0.1"})
    with urlopen(request, timeout=25) as response:
        xml = response.read()

    root = ElementTree.fromstring(xml)
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else []
    captured_at = datetime.now(UTC).isoformat()

    signals = []
    for index, item in enumerate(items):
        title = _text(item, "title")
        approx_traffic = _ht_text(item, "approx_traffic")
        news_titles = [
            _ht_text(news_item, "news_item_title")
            for news_item in item.findall("{https://trends.google.com/trending/rss}news_item")
        ]
        signals.append(
            {
                "id": f"trend-{geo.lower()}-{index + 1:03d}",
                "cluster_key": f"trend-{slugify(title)}",
                "source": "Google Trends RSS",
                "source_url": _text(item, "link") or url,
                "captured_at": captured_at,
                "region": geo,
                "evidence_type": "trend",
                "strength": "high" if index < 5 else "medium",
                "title": title,
                "summary": _text(item, "description") or "; ".join([value for value in news_titles if value][:2]),
                "tags": ["trend", "demand"],
                "metrics": {
                    "approx_traffic": approx_traffic,
                    "traffic_value": _traffic_value(approx_traffic),
                    "published": _text(item, "pubDate")
                }
            }
        )

    return {
        "run_name": f"google-trends-{geo.lower()}",
        "captured_at": captured_at,
        "signals": signals,
    }
