from __future__ import annotations

from html import escape
from typing import Any


COLUMNS = [
    ("TESTAR AGORA", "test-now"),
    ("DEEPDIVE", "deepdive"),
    ("RADAR", "radar"),
    ("DESCARTAR", "discard"),
]


def _score(opportunity: dict[str, Any], key: str) -> str:
    return str(opportunity.get("scores", {}).get(key, 0))


def _evidence_links(opportunity: dict[str, Any]) -> str:
    links = []
    for item in opportunity.get("evidence", [])[:5]:
        title = escape(item.get("title") or item.get("source") or "evidencia")
        url = escape(item.get("url") or "")
        label = escape(item.get("source") or "fonte")
        if url:
            links.append(f'<a href="{url}" target="_blank" rel="noreferrer">{label}: {title}</a>')
        else:
            links.append(f"<span>{label}: {title}</span>")
    return "".join(f"<li>{link}</li>" for link in links) or "<li>Sem links</li>"


def _scale_proofs(opportunity: dict[str, Any]) -> str:
    rows = []
    for item in opportunity.get("evidence", []):
        metrics = item.get("metrics") or {}
        examples = [
            *(metrics.get("global_duplicate_examples") or []),
            *(metrics.get("duplicate_examples") or []),
        ]
        if not examples:
            continue
        rows.append(
            "<li><strong>{query}</strong>: escala {scale}, global {global_scale}, cross-source {cross}, cross-domain {domain}, global cross-domain {global_domain}</li>".format(
                query=escape(str(metrics.get("query") or item.get("title") or "Meta Ads")),
                scale=escape(str(metrics.get("scale_signal", "unknown"))),
                global_scale=escape(str(metrics.get("global_scale_signal", "none"))),
                cross=escape(str(metrics.get("cross_source_duplicate_groups", 0))),
                domain=escape(str(metrics.get("cross_domain_duplicate_groups", 0))),
                global_domain=escape(str(metrics.get("global_cross_domain_duplicate_groups", 0))),
            )
        )
        for example in examples[:2]:
            pages = ", ".join(example.get("source_pages") or [example.get("page_name", "")])
            domains = ", ".join(example.get("destination_domains") or [])
            ids = ", ".join(example.get("library_ids") or [example.get("library_id", "")])
            queries = ", ".join(example.get("queries") or [])
            rows.append(
                "<li>Prova: {kind} | paginas: {pages} | dominios: {domains} | queries: {queries} | IDs: {ids}</li>".format(
                    kind=escape(str(example.get("type", "duplicate"))),
                    pages=escape(pages or "n/a"),
                    domains=escape(domains or "n/a"),
                    queries=escape(queries or "n/a"),
                    ids=escape(ids or "n/a"),
                )
            )
    return "".join(rows) or "<li>Nenhum duplicado escalado detectado nesta rodada.</li>"


def _list(items: list[str]) -> str:
    return "".join(f"<li>{escape(str(item))}</li>" for item in items[:4]) or "<li>A definir</li>"


def _card(opportunity: dict[str, Any]) -> str:
    scores = opportunity.get("scores", {})
    decision_class = {
        "TESTAR AGORA": "test-now",
        "DEEPDIVE": "deepdive",
        "RADAR": "radar",
        "DESCARTAR": "discard",
    }.get(scores.get("decision"), "radar")

    return f"""
    <article class="card {decision_class}">
      <div class="card-head">
        <span class="pill">{escape(scores.get("decision", ""))}</span>
        <span class="score">{_score(opportunity, "overall")}</span>
      </div>
      <h3>{escape(opportunity.get("title", "Sem titulo"))}</h3>
      <p class="type">{escape(opportunity.get("offer_type") or opportunity.get("solution_type") or "")}</p>
      <p><strong>Publico:</strong> {escape(opportunity.get("audience", ""))}</p>
      <p><strong>Promessa:</strong> {escape(opportunity.get("promise", ""))}</p>
      <div class="metrics">
        <span>Market {_score(opportunity, "market")}</span>
        <span>MVP {_score(opportunity, "mvp")}</span>
        <span>Conf {_score(opportunity, "confidence")}</span>
        <span>Meta {_score(opportunity, "meta_ads_fit")}</span>
      </div>
      <details>
        <summary>MVP minimo</summary>
        <ul>{_list(opportunity.get("mvp", []))}</ul>
      </details>
      <details>
        <summary>Evidencias</summary>
        <ul>{_evidence_links(opportunity)}</ul>
      </details>
      <details>
        <summary>Escala/duplicados</summary>
        <ul>{_scale_proofs(opportunity)}</ul>
      </details>
      <details>
        <summary>Red team</summary>
        <ul>{_list(opportunity.get("red_team", []))}</ul>
      </details>
    </article>
    """


def render_html_kanban(result: dict[str, Any]) -> str:
    opportunities = result.get("opportunities", [])
    by_decision: dict[str, list[dict[str, Any]]] = {name: [] for name, _class_name in COLUMNS}
    for opportunity in opportunities:
        decision = opportunity.get("scores", {}).get("decision", "RADAR")
        by_decision.setdefault(decision, []).append(opportunity)

    columns = []
    for decision, class_name in COLUMNS:
        cards = "\n".join(_card(opportunity) for opportunity in by_decision.get(decision, []))
        columns.append(
            f"""
            <section class="column {class_name}">
              <header>
                <h2>{decision}</h2>
                <span>{len(by_decision.get(decision, []))}</span>
              </header>
              {cards or '<div class="empty">Sem cards nesta coluna.</div>'}
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gotham Opportunity Kanban</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --ink: #15171a;
      --muted: #5c6570;
      --line: #d8dde4;
      --card: #ffffff;
      --green: #137a45;
      --blue: #2359c4;
      --amber: #9a5b00;
      --red: #ad2b2b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    .topbar {{
      padding: 24px 28px 16px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; letter-spacing: 0; }}
    .summary {{ color: var(--muted); display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px; }}
    .notice {{
      margin-top: 14px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fafafa;
      color: var(--muted);
    }}
    .board {{
      display: grid;
      grid-template-columns: repeat(4, minmax(280px, 1fr));
      gap: 16px;
      padding: 18px;
      align-items: start;
      overflow-x: auto;
    }}
    .column {{
      min-height: 420px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #eef1f5;
      padding: 12px;
    }}
    .column header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .column h2 {{ margin: 0; font-size: 14px; letter-spacing: 0; }}
    .column header span {{
      min-width: 28px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--line);
      font-size: 13px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-left: 5px solid var(--blue);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 12px;
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }}
    .card.test-now {{ border-left-color: var(--green); }}
    .card.deepdive {{ border-left-color: var(--blue); }}
    .card.radar {{ border-left-color: var(--amber); }}
    .card.discard {{ border-left-color: var(--red); }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      background: #f0f3f7;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .score {{
      font-size: 24px;
      font-weight: 800;
    }}
    h3 {{ margin: 12px 0 6px; font-size: 17px; line-height: 1.25; letter-spacing: 0; }}
    p {{ margin: 8px 0; color: #252a31; font-size: 14px; line-height: 1.45; }}
    .type {{ color: var(--muted); font-size: 13px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6px;
      margin: 12px 0;
    }}
    .metrics span {{
      background: #f7f8fa;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 12px;
      color: var(--muted);
    }}
    details {{
      border-top: 1px solid var(--line);
      padding-top: 8px;
      margin-top: 8px;
    }}
    summary {{ cursor: pointer; font-weight: 700; font-size: 13px; }}
    ul {{ padding-left: 18px; margin: 8px 0 0; }}
    li {{ margin: 6px 0; font-size: 13px; line-height: 1.35; }}
    a {{ color: #164aa8; text-decoration: none; overflow-wrap: anywhere; }}
    a:hover {{ text-decoration: underline; }}
    .empty {{
      border: 1px dashed #c3cad4;
      border-radius: 8px;
      padding: 16px;
      color: var(--muted);
      background: rgba(255,255,255,.5);
      font-size: 14px;
    }}
    @media (max-width: 1100px) {{
      .board {{ grid-template-columns: repeat(2, minmax(280px, 1fr)); }}
    }}
    @media (max-width: 700px) {{
      .board {{ grid-template-columns: 1fr; padding: 12px; }}
      .topbar {{ padding: 18px 16px; }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <h1>Gotham Opportunity Kanban</h1>
    <div class="summary">
      <span>Run: {escape(result.get("run_name", ""))}</span>
      <span>Gerado: {escape(result.get("generated_at", ""))}</span>
      <span>Sinais: {result.get("signal_count", 0)}</span>
      <span>Promissoras: {result.get("promising_count", 0)}/{result.get("min_promising_target", 5)}</span>
      <span>Status: {escape(result.get("round_status", ""))}</span>
    </div>
    <div class="notice">{escape(result.get("round_note", ""))}</div>
  </header>
  <main class="board">
    {''.join(columns)}
  </main>
</body>
</html>
"""
