from __future__ import annotations

from html import escape
from typing import Any


DECISION_ORDER = ["TESTAR AGORA", "DEEPDIVE", "RADAR", "DESCARTAR"]
DECISION_CLASS = {
    "TESTAR AGORA": "test-now",
    "DEEPDIVE": "deepdive",
    "RADAR": "radar",
    "DESCARTAR": "discard",
}
DECISION_LABEL = {
    "TESTAR AGORA": "Pronto para teste",
    "DEEPDIVE": "Investigar mais",
    "RADAR": "Observar",
    "DESCARTAR": "Cortar",
}


def _text(value: Any) -> str:
    return escape(str(value or ""))


def _score(opportunity: dict[str, Any], key: str) -> int:
    value = opportunity.get("scores", {}).get(key, 0)
    return int(value) if isinstance(value, int | float) else 0


def _score_class(value: int) -> str:
    if value >= 78:
        return "score-strong"
    if value >= 65:
        return "score-good"
    if value >= 50:
        return "score-watch"
    return "score-weak"


def _bar(value: int) -> str:
    width = max(0, min(100, value))
    return f"""
    <span class="bar" aria-label="score {width}">
      <span style="width:{width}%"></span>
    </span>
    """


def _decision(opportunity: dict[str, Any]) -> str:
    return str(opportunity.get("scores", {}).get("decision") or "RADAR")


def _decision_badge(decision: str) -> str:
    class_name = DECISION_CLASS.get(decision, "radar")
    label = DECISION_LABEL.get(decision, decision)
    return f'<span class="badge {class_name}">{_text(label)}</span>'


def _evidence_counts(opportunity: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in opportunity.get("evidence", []):
        kind = str(item.get("type") or "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _metric(opportunity: dict[str, Any], key: str) -> int:
    for item in opportunity.get("evidence", []):
        metrics = item.get("metrics") or {}
        value = metrics.get(key)
        if isinstance(value, int | float):
            return int(value)
    return 0


def _scale_level(opportunity: dict[str, Any]) -> str:
    levels = []
    for item in opportunity.get("evidence", []):
        metrics = item.get("metrics") or {}
        for key in ("global_scale_signal", "scale_signal"):
            level = str(metrics.get(key) or "").lower()
            if level:
                levels.append(level)
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    if "low" in levels:
        return "low"
    return "none"


def _scale_label(level: str) -> str:
    return {
        "high": "Escala forte",
        "medium": "Escala média",
        "low": "Escala fraca",
        "none": "Sem prova de escala",
    }.get(level, "Sem prova de escala")


def _list(items: list[str], limit: int = 4) -> str:
    rows = [f"<li>{_text(item)}</li>" for item in items[:limit]]
    return "".join(rows) or "<li>A definir</li>"


def _source_chips(opportunity: dict[str, Any]) -> str:
    sources = []
    seen = set()
    for item in opportunity.get("evidence", []):
        source = str(item.get("source") or "fonte")
        if source in seen:
            continue
        seen.add(source)
        sources.append(f'<span class="chip">{_text(source)}</span>')
    return "".join(sources[:8]) or '<span class="chip muted">Sem fonte</span>'


def _type_chips(opportunity: dict[str, Any]) -> str:
    counts = _evidence_counts(opportunity)
    if not counts:
        return '<span class="chip muted">Sem evidência</span>'
    return "".join(
        f'<span class="chip">{_text(kind)} {count}</span>'
        for kind, count in sorted(counts.items())
    )


def _ranking_rows(opportunities: list[dict[str, Any]]) -> str:
    rows = []
    for index, opportunity in enumerate(opportunities, start=1):
        scores = opportunity.get("scores", {})
        overall = _score(opportunity, "overall")
        decision = _decision(opportunity)
        scale = _scale_level(opportunity)
        rows.append(
            f"""
            <tr>
              <td class="rank">#{index}</td>
              <td>
                <strong>{_text(opportunity.get("title"))}</strong>
                <small>{_text(opportunity.get("offer_type") or opportunity.get("solution_type"))}</small>
              </td>
              <td>{_decision_badge(decision)}</td>
              <td><span class="big-score {_score_class(overall)}">{overall}</span>{_bar(overall)}</td>
              <td>{_score(opportunity, "market")}</td>
              <td>{_score(opportunity, "pain")}</td>
              <td>{_score(opportunity, "distribution")}</td>
              <td>{_score(opportunity, "mvp")}</td>
              <td>{_score(opportunity, "evidence_quality")}</td>
              <td>{_score(opportunity, "proof_density")}</td>
              <td>{_score(opportunity, "confidence")}</td>
              <td><span class="scale-dot {scale}"></span>{_text(_scale_label(scale))}</td>
              <td>{_metric(opportunity, "active_ads")}</td>
              <td>{_metric(opportunity, "global_duplicate_groups")}</td>
            </tr>
            """
        )
    return "".join(rows)


def _kanban_cards(opportunities: list[dict[str, Any]], decision: str) -> str:
    selected = [item for item in opportunities if _decision(item) == decision]
    if not selected:
        return '<div class="empty">Sem oportunidades aqui.</div>'
    cards = []
    for opportunity in selected:
        overall = _score(opportunity, "overall")
        scale = _scale_level(opportunity)
        cards.append(
            f"""
            <article class="mini-card {DECISION_CLASS.get(decision, 'radar')}">
              <div class="mini-head">
                <span>{_text(opportunity.get("offer_type") or opportunity.get("solution_type"))}</span>
                <strong>{overall}</strong>
              </div>
              <h3>{_text(opportunity.get("title"))}</h3>
              <p>{_text(opportunity.get("promise"))}</p>
              <div class="mini-metrics">
                <span>MVP {_score(opportunity, "mvp")}</span>
                <span>Meta {_score(opportunity, "meta_ads_fit")}</span>
                <span>{_text(_scale_label(scale))}</span>
              </div>
            </article>
            """
        )
    return "".join(cards)


def _kanban(opportunities: list[dict[str, Any]]) -> str:
    columns = []
    for decision in DECISION_ORDER:
        columns.append(
            f"""
            <section class="kanban-col">
              <header>
                <h3>{_text(DECISION_LABEL.get(decision, decision))}</h3>
                <span>{len([item for item in opportunities if _decision(item) == decision])}</span>
              </header>
              {_kanban_cards(opportunities, decision)}
            </section>
            """
        )
    return "".join(columns)


def _proof_rows(opportunity: dict[str, Any]) -> str:
    rows = []
    for item in opportunity.get("evidence", []):
        metrics = item.get("metrics") or {}
        examples = [
            *(metrics.get("global_duplicate_examples") or []),
            *(metrics.get("duplicate_examples") or []),
        ]
        if not examples:
            continue
        for example in examples[:4]:
            pages = ", ".join(example.get("source_pages") or [example.get("page_name", "")])
            domains = ", ".join(example.get("destination_domains") or [])
            queries = ", ".join(example.get("queries") or [])
            ids = ", ".join(example.get("library_ids") or [example.get("library_id", "")])
            rows.append(
                f"""
                <tr>
                  <td>{_text(opportunity.get("title"))}</td>
                  <td>{_text(example.get("type", "duplicate"))}</td>
                  <td>{_text(pages or "n/a")}</td>
                  <td>{_text(domains or "n/a")}</td>
                  <td>{_text(queries or metrics.get("query") or "n/a")}</td>
                  <td>{_text(ids or "n/a")}</td>
                  <td>{_text(example.get("proof") or "fingerprint/copy normalizada")}</td>
                </tr>
                """
            )
    return "".join(rows)


def _all_proofs(opportunities: list[dict[str, Any]]) -> str:
    rows = "".join(_proof_rows(opportunity) for opportunity in opportunities)
    if not rows:
        return """
        <tr>
          <td colspan="7" class="empty-row">Nenhuma prova de escala duplicada apareceu nesta rodada.</td>
        </tr>
        """
    return rows


def _evidence_rows(opportunity: dict[str, Any]) -> str:
    rows = []
    for item in opportunity.get("evidence", [])[:10]:
        url = str(item.get("url") or "")
        title = _text(item.get("title"))
        title_html = f'<a href="{_text(url)}" target="_blank" rel="noreferrer">{title}</a>' if url else title
        rows.append(
            f"""
            <li>
              <span class="evidence-kind">{_text(item.get("type"))}/{_text(item.get("strength"))}</span>
              <span class="quality-pill { _text(str((item.get('metrics') or {}).get('quality_verdict', 'weak'))) }">Q{_text((item.get("metrics") or {}).get("quality_score", ""))}</span>
              {title_html}
              <small>{_text(item.get("source"))}</small>
            </li>
            """
        )
    return "".join(rows) or "<li>Sem evidências anexadas.</li>"


def _dossiers(opportunities: list[dict[str, Any]]) -> str:
    cards = []
    for opportunity in opportunities:
        scores = opportunity.get("scores", {})
        scale = _scale_level(opportunity)
        test = opportunity.get("meta_ads_test") or {}
        cards.append(
            f"""
            <article class="dossier">
              <header>
                <div>
                  <span class="eyebrow">{_text(opportunity.get("offer_type") or opportunity.get("solution_type"))}</span>
                  <h3>{_text(opportunity.get("title"))}</h3>
                </div>
                <div class="score-stack">
                  {_decision_badge(str(scores.get("decision") or "RADAR"))}
                  <strong>{_score(opportunity, "overall")}</strong>
                </div>
              </header>
              <div class="dossier-grid">
                <section>
                  <h4>Oferta</h4>
                  <p><strong>Público:</strong> {_text(opportunity.get("audience"))}</p>
                  <p><strong>Promessa:</strong> {_text(opportunity.get("promise"))}</p>
                  <p><strong>Por que agora:</strong> {_text(opportunity.get("why_now"))}</p>
                  <div class="chips">{_type_chips(opportunity)}</div>
                  <div class="chips">{_source_chips(opportunity)}</div>
                </section>
                <section>
                  <h4>Métricas</h4>
                  <div class="metric-list">
                    <span>Market <b>{_score(opportunity, "market")}</b></span>
                    <span>Dor <b>{_score(opportunity, "pain")}</b></span>
                    <span>Distribuição <b>{_score(opportunity, "distribution")}</b></span>
                    <span>MVP <b>{_score(opportunity, "mvp")}</b></span>
                    <span>Qualidade <b>{_score(opportunity, "evidence_quality")}</b></span>
                    <span>Densidade <b>{_score(opportunity, "proof_density")}</b></span>
                    <span>Confiança <b>{_score(opportunity, "confidence")}</b></span>
                    <span>Meta fit <b>{_score(opportunity, "meta_ads_fit")}</b></span>
                    <span>{_text(_scale_label(scale))} <b>{_metric(opportunity, "global_duplicate_groups")}</b></span>
                  </div>
                </section>
                <section>
                  <h4>MVP mínimo</h4>
                  <ul>{_list(opportunity.get("mvp", []), 5)}</ul>
                </section>
                <section>
                  <h4>Teste Meta Ads</h4>
                  <ul>
                    <li>Budget: {_text(test.get("budget", "R$300-R$700"))}</li>
                    <li>Criativos: {_text(test.get("creatives", 4))}</li>
                    <li>Objetivo: {_text(test.get("objective", "Lead ou compra"))}</li>
                    <li>Matar se: {_text(test.get("kill_rule", "Sem sinal após gasto mínimo"))}</li>
                    <li>Escalar se: {_text(test.get("scale_rule", "Lead barato ou primeira venda"))}</li>
                  </ul>
                </section>
                <section>
                  <h4>Evidências</h4>
                  <ul class="evidence-list">{_evidence_rows(opportunity)}</ul>
                </section>
                <section>
                  <h4>Red team</h4>
                  <ul>{_list(opportunity.get("red_team", []), 5)}</ul>
                </section>
              </div>
            </article>
            """
        )
    return "".join(cards)


def _map_rows(opportunities: list[dict[str, Any]]) -> str:
    rows = []
    for opportunity in opportunities:
        pain_terms = opportunity.get("pain_terms", [])[:4]
        offer_terms = opportunity.get("offer_terms", [])[:4]
        scale = _scale_level(opportunity)
        rows.append(
            f"""
            <article class="map-row">
              <div class="map-node main">
                <small>Oferta</small>
                <strong>{_text(opportunity.get("title"))}</strong>
              </div>
              <div class="map-arrow">-&gt;</div>
              <div class="map-node">
                <small>Dores</small>
                <div class="chips">{''.join(f'<span class="chip">{_text(item)}</span>' for item in pain_terms) or '<span class="chip muted">A definir</span>'}</div>
              </div>
              <div class="map-arrow">-&gt;</div>
              <div class="map-node">
                <small>Peças de venda</small>
                <div class="chips">{''.join(f'<span class="chip">{_text(item)}</span>' for item in offer_terms) or '<span class="chip muted">A definir</span>'}</div>
              </div>
              <div class="map-arrow">-&gt;</div>
              <div class="map-node">
                <small>Prova</small>
                <strong>{_text(_scale_label(scale))}</strong>
                <span>{_metric(opportunity, "active_ads")} ads ativos</span>
              </div>
            </article>
            """
        )
    return "".join(rows)


def _experiment_rows(opportunities: list[dict[str, Any]]) -> str:
    rows = []
    for opportunity in opportunities:
        test = opportunity.get("meta_ads_test") or {}
        rows.append(
            f"""
            <tr>
              <td><strong>{_text(opportunity.get("title"))}</strong></td>
              <td>{_text(test.get("budget", "R$300-R$700"))}</td>
              <td>{_text(test.get("creatives", 4))}</td>
              <td>{_text(test.get("objective", "Lead ou compra"))}</td>
              <td>{_text(test.get("kill_rule", "Sem sinal após gasto mínimo"))}</td>
              <td>{_text(test.get("scale_rule", "Lead barato ou primeira venda"))}</td>
              <td>{_text(opportunity.get("mvp_hours", 72))}h</td>
            </tr>
            """
        )
    return "".join(rows)


def _source_rows(opportunities: list[dict[str, Any]]) -> str:
    rows = []
    for opportunity in opportunities:
        for item in opportunity.get("evidence", []):
            metrics = item.get("metrics") or {}
            problems = "; ".join(metrics.get("quality_problems") or [])
            strengths = "; ".join(metrics.get("quality_strengths") or [])
            url = str(item.get("url") or "")
            title = _text(item.get("title"))
            title_html = f'<a href="{_text(url)}" target="_blank" rel="noreferrer">{title}</a>' if url else title
            rows.append(
                f"""
                <tr>
                  <td>{_text(opportunity.get("title"))}</td>
                  <td>{_text(item.get("source"))}</td>
                  <td>{_text(item.get("type"))}</td>
                  <td>{_text(metrics.get("quality_verdict"))}</td>
                  <td>{_text(metrics.get("quality_score"))}</td>
                  <td>{_text(metrics.get("source_tier"))}</td>
                  <td>{title_html}</td>
                  <td>{_text(strengths or "n/a")}</td>
                  <td>{_text(problems or "n/a")}</td>
                </tr>
                """
            )
    return "".join(rows) or '<tr><td colspan="9" class="empty-row">Sem fontes anexadas.</td></tr>'


def _stat(value: Any, label: str, tone: str = "") -> str:
    return f"""
    <div class="stat {tone}">
      <strong>{_text(value)}</strong>
      <span>{_text(label)}</span>
    </div>
    """


def render_html_war_room(result: dict[str, Any]) -> str:
    opportunities = result.get("opportunities", [])
    top_score = max((_score(item, "overall") for item in opportunities), default=0)
    active_ads = sum(_metric(item, "active_ads") for item in opportunities)
    scaled = sum(1 for item in opportunities if _scale_level(item) in {"high", "medium"})
    tabs = [
        ("ranking", "Ranking", "R"),
        ("kanban", "Kanban", "K"),
        ("dossiers", "Dossiês", "D"),
        ("sources", "Fontes", "F"),
        ("proofs", "Provas", "P"),
        ("map", "Mapa", "M"),
        ("experiments", "Experimentos", "E"),
    ]
    tab_buttons = "".join(
        f'<button class="tab-button{" active" if index == 0 else ""}" data-tab="{key}"><span>{icon}</span>{label}</button>'
        for index, (key, label, icon) in enumerate(tabs)
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gotham Opportunity War Room</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f6f8;
      --panel: #ffffff;
      --ink: #15181d;
      --muted: #626b78;
      --line: #d9dee7;
      --line-strong: #bdc6d3;
      --green: #16834f;
      --blue: #2459c9;
      --amber: #a15f00;
      --red: #b3323a;
      --violet: #6941c6;
      --teal: #08736b;
      --soft-green: #eaf7ef;
      --soft-blue: #edf3ff;
      --soft-amber: #fff5df;
      --soft-red: #fff0f1;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    a {{ color: #164aa8; text-decoration: none; overflow-wrap: anywhere; }}
    a:hover {{ text-decoration: underline; }}
    .shell {{ min-height: 100vh; }}
    .hero {{
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      padding: 22px 28px;
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    .hero-main {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      max-width: 1600px;
      margin: 0 auto;
    }}
    h1 {{ margin: 0; font-size: 26px; line-height: 1.15; letter-spacing: 0; }}
    .subtitle {{ margin: 8px 0 0; color: var(--muted); font-size: 14px; max-width: 880px; line-height: 1.45; }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      padding: 5px 12px;
      border-radius: 999px;
      background: var(--soft-blue);
      color: var(--blue);
      border: 1px solid #c9d8ff;
      font-weight: 800;
      font-size: 12px;
      white-space: nowrap;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(6, minmax(130px, 1fr));
      gap: 10px;
      max-width: 1600px;
      margin: 18px auto 0;
    }}
    .stat {{
      border: 1px solid var(--line);
      background: #fafbfc;
      border-radius: 8px;
      padding: 10px 12px;
      min-height: 66px;
    }}
    .stat strong {{ display: block; font-size: 22px; line-height: 1; }}
    .stat span {{ display: block; margin-top: 8px; color: var(--muted); font-size: 12px; }}
    .stat.green {{ background: var(--soft-green); border-color: #c6e8d2; }}
    .stat.blue {{ background: var(--soft-blue); border-color: #c9d8ff; }}
    .stat.amber {{ background: var(--soft-amber); border-color: #f1d69c; }}
    .tabs {{
      max-width: 1600px;
      margin: 14px auto 0;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .tab-button {{
      border: 1px solid var(--line);
      background: #fff;
      color: #2b313b;
      min-height: 38px;
      padding: 6px 11px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      font-weight: 800;
      font-size: 13px;
    }}
    .tab-button span {{
      width: 22px;
      height: 22px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
      background: #eef1f5;
      color: var(--blue);
      font-size: 12px;
    }}
    .tab-button.active {{ border-color: #9bb6ef; background: var(--soft-blue); color: var(--blue); }}
    .content {{ max-width: 1600px; margin: 0 auto; padding: 18px 28px 32px; }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    .panel-head {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }}
    .panel-head h2 {{ margin: 0; font-size: 17px; letter-spacing: 0; }}
    .panel-head p {{ margin: 4px 0 0; color: var(--muted); font-size: 13px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1040px; }}
    th, td {{ padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #f7f8fa; color: #46505d; font-size: 12px; text-transform: uppercase; letter-spacing: .02em; }}
    td small {{ display: block; color: var(--muted); margin-top: 3px; }}
    .rank {{ color: var(--muted); font-weight: 800; width: 52px; }}
    .big-score {{ display: inline-block; font-size: 22px; font-weight: 900; min-width: 34px; }}
    .score-strong {{ color: var(--green); }}
    .score-good {{ color: var(--blue); }}
    .score-watch {{ color: var(--amber); }}
    .score-weak {{ color: var(--red); }}
    .bar {{ display: block; height: 7px; width: 86px; background: #eef1f5; border-radius: 999px; overflow: hidden; margin-top: 5px; }}
    .bar span {{ display: block; height: 100%; background: currentColor; border-radius: inherit; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 900;
      white-space: nowrap;
    }}
    .badge.test-now {{ background: var(--soft-green); color: var(--green); border: 1px solid #b8dfc6; }}
    .badge.deepdive {{ background: var(--soft-blue); color: var(--blue); border: 1px solid #c9d8ff; }}
    .badge.radar {{ background: var(--soft-amber); color: var(--amber); border: 1px solid #f1d69c; }}
    .badge.discard {{ background: var(--soft-red); color: var(--red); border: 1px solid #f0c2c6; }}
    .scale-dot {{
      display: inline-block;
      width: 9px;
      height: 9px;
      border-radius: 999px;
      margin-right: 7px;
      background: var(--line-strong);
    }}
    .scale-dot.high {{ background: var(--green); }}
    .scale-dot.medium {{ background: var(--blue); }}
    .scale-dot.low {{ background: var(--amber); }}
    .board {{
      display: grid;
      grid-template-columns: repeat(4, minmax(260px, 1fr));
      gap: 12px;
      align-items: start;
    }}
    .kanban-col {{
      background: #eef1f5;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-height: 360px;
    }}
    .kanban-col header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }}
    .kanban-col h3 {{ margin: 0; font-size: 14px; letter-spacing: 0; }}
    .kanban-col header span {{
      min-width: 26px;
      min-height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 900;
    }}
    .mini-card {{
      background: #fff;
      border: 1px solid var(--line);
      border-left: 5px solid var(--blue);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 10px;
    }}
    .mini-card.test-now {{ border-left-color: var(--green); }}
    .mini-card.deepdive {{ border-left-color: var(--blue); }}
    .mini-card.radar {{ border-left-color: var(--amber); }}
    .mini-card.discard {{ border-left-color: var(--red); }}
    .mini-head {{ display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 12px; }}
    .mini-head strong {{ color: var(--ink); font-size: 18px; }}
    .mini-card h3 {{ margin: 8px 0 6px; font-size: 15px; line-height: 1.25; }}
    .mini-card p {{ margin: 0; font-size: 13px; color: #2e3440; line-height: 1.4; }}
    .mini-metrics {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }}
    .mini-metrics span, .chip {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f7f8fa;
      color: #4b5563;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
    }}
    .chip.muted {{ color: var(--muted); }}
    .dossier {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 14px;
      overflow: hidden;
    }}
    .dossier > header {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      padding: 15px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
    }}
    .eyebrow {{ color: var(--muted); font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: .03em; }}
    .dossier h3 {{ margin: 4px 0 0; font-size: 20px; line-height: 1.25; }}
    .score-stack {{ display: flex; gap: 10px; align-items: center; }}
    .score-stack strong {{ font-size: 30px; }}
    .dossier-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(280px, 1fr));
      gap: 0;
    }}
    .dossier-grid section {{ padding: 15px 16px; border-bottom: 1px solid var(--line); }}
    .dossier-grid section:nth-child(odd) {{ border-right: 1px solid var(--line); }}
    h4 {{ margin: 0 0 10px; font-size: 14px; letter-spacing: 0; }}
    p {{ font-size: 13px; line-height: 1.45; color: #2f3742; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin: 6px 0; font-size: 13px; line-height: 1.4; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
    .metric-list {{ display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 8px; }}
    .metric-list span {{
      border: 1px solid var(--line);
      background: #f7f8fa;
      border-radius: 8px;
      padding: 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .metric-list b {{ display: block; color: var(--ink); font-size: 18px; margin-top: 3px; }}
    .evidence-list {{ padding-left: 0; list-style: none; }}
    .evidence-list li {{ border-bottom: 1px solid #eef1f5; padding-bottom: 8px; }}
    .evidence-kind {{
      display: inline-flex;
      margin-right: 6px;
      color: var(--violet);
      font-weight: 900;
      font-size: 12px;
    }}
    .quality-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 20px;
      padding: 2px 6px;
      margin-right: 6px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #f7f8fa;
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
    }}
    .quality-pill.strong {{ background: var(--soft-green); color: var(--green); border-color: #b8dfc6; }}
    .quality-pill.usable {{ background: var(--soft-blue); color: var(--blue); border-color: #c9d8ff; }}
    .quality-pill.weak {{ background: var(--soft-amber); color: var(--amber); border-color: #f1d69c; }}
    .quality-pill.noise {{ background: var(--soft-red); color: var(--red); border-color: #f0c2c6; }}
    .map-row {{
      display: grid;
      grid-template-columns: minmax(220px, 1.2fr) 28px minmax(180px, 1fr) 28px minmax(180px, 1fr) 28px minmax(160px, .8fr);
      gap: 8px;
      align-items: stretch;
      margin-bottom: 10px;
    }}
    .map-node {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 8px;
      padding: 12px;
      min-height: 88px;
    }}
    .map-node.main {{ border-left: 5px solid var(--teal); }}
    .map-node small {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
    .map-node strong {{ display: block; font-size: 14px; line-height: 1.3; }}
    .map-node span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .map-arrow {{
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--muted);
      font-weight: 900;
    }}
    .empty, .empty-row {{
      color: var(--muted);
      background: #fafbfc;
      border: 1px dashed #c7ced9;
      border-radius: 8px;
      padding: 14px;
      font-size: 13px;
    }}
    .empty-row {{ text-align: center; border-radius: 0; }}
    @media (max-width: 1180px) {{
      .stats {{ grid-template-columns: repeat(3, minmax(130px, 1fr)); }}
      .board {{ grid-template-columns: repeat(2, minmax(260px, 1fr)); }}
      .map-row {{ grid-template-columns: 1fr; }}
      .map-arrow {{ display: none; }}
    }}
    @media (max-width: 760px) {{
      .hero {{ position: static; padding: 18px 14px; }}
      .hero-main {{ display: block; }}
      .status-pill {{ margin-top: 12px; }}
      .stats {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      .content {{ padding: 14px; }}
      .board {{ grid-template-columns: 1fr; }}
      .dossier > header {{ display: block; }}
      .score-stack {{ margin-top: 12px; }}
      .dossier-grid {{ grid-template-columns: 1fr; }}
      .dossier-grid section:nth-child(odd) {{ border-right: 0; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-main">
        <div>
          <h1>Gotham Opportunity War Room</h1>
          <p class="subtitle">
            Run: {_text(result.get("run_name"))} · Gerado em {_text(result.get("generated_at"))}.
            Este painel separa decisão, evidência, escala e execução para acelerar testes sem perder rastreabilidade.
          </p>
        </div>
        <span class="status-pill">{_text(result.get("round_status"))}</span>
      </div>
      <div class="stats">
        {_stat(result.get("signal_count", 0), "sinais analisados")}
        {_stat(result.get("source_count", 0), "fontes únicas")}
        {_stat(len(opportunities), "oportunidades ranqueadas")}
        {_stat(result.get("promising_count", 0), "promissoras", "green")}
        {_stat(top_score, "maior score", "blue")}
        {_stat(f"{active_ads}/{scaled}", "ads ativos / com escala", "amber")}
      </div>
      <nav class="tabs" aria-label="War Room tabs">
        {tab_buttons}
      </nav>
    </header>
    <main class="content">
      <section id="ranking" class="tab-panel active">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Ranking comparativo</h2>
              <p>Use esta tabela para decidir onde colocar atenção, verba e produção de MVP.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th><th>Oportunidade</th><th>Decisão</th><th>Score</th>
                  <th>Market</th><th>Dor</th><th>Distrib.</th><th>MVP</th><th>Qual.</th><th>Provas</th><th>Conf.</th>
                  <th>Escala</th><th>Ads</th><th>Dup.</th>
                </tr>
              </thead>
              <tbody>{_ranking_rows(opportunities)}</tbody>
            </table>
          </div>
        </div>
      </section>
      <section id="kanban" class="tab-panel">
        <div class="board">{_kanban(opportunities)}</div>
      </section>
      <section id="dossiers" class="tab-panel">
        {_dossiers(opportunities)}
      </section>
      <section id="sources" class="tab-panel">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Fontes auditáveis</h2>
              <p>Cada linha mostra origem, tipo de prova, qualidade, pontos fortes e problemas. Fonte fraca não deve sustentar gasto.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Oportunidade</th><th>Fonte</th><th>Tipo</th><th>Veredito</th><th>Q</th>
                  <th>Tier</th><th>Prova</th><th>Forças</th><th>Problemas</th>
                </tr>
              </thead>
              <tbody>{_source_rows(opportunities)}</tbody>
            </table>
          </div>
        </div>
      </section>
      <section id="proofs" class="tab-panel">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Provas de escala e duplicação</h2>
              <p>Páginas, domínios, queries e IDs usados para justificar sinais de anúncio escalado.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Oportunidade</th><th>Tipo</th><th>Páginas</th><th>Domínios</th>
                  <th>Queries</th><th>IDs</th><th>Prova</th>
                </tr>
              </thead>
              <tbody>{_all_proofs(opportunities)}</tbody>
            </table>
          </div>
        </div>
      </section>
      <section id="map" class="tab-panel">
        {_map_rows(opportunities)}
      </section>
      <section id="experiments" class="tab-panel">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Fila de experimentos</h2>
              <p>Resumo prático para transformar oportunidade em LP, criativos e teste Meta Ads.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Oportunidade</th><th>Budget</th><th>Criativos</th><th>Objetivo</th>
                  <th>Kill rule</th><th>Scale rule</th><th>MVP</th>
                </tr>
              </thead>
              <tbody>{_experiment_rows(opportunities)}</tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  </div>
  <script>
    const buttons = [...document.querySelectorAll('.tab-button')];
    const panels = [...document.querySelectorAll('.tab-panel')];
    buttons.forEach((button) => {{
      button.addEventListener('click', () => {{
        const target = button.dataset.tab;
        buttons.forEach((item) => item.classList.toggle('active', item === button));
        panels.forEach((panel) => panel.classList.toggle('active', panel.id === target));
      }});
    }});
  </script>
</body>
</html>
"""
