from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .agent import run_opportunity_research
from .collectors.google_trends_rss import collect_google_trends_daily
from .collectors.reddit_search import collect_reddit_search
from .exporters.html_kanban import render_html_kanban
from .exporters.html_war_room import render_html_war_room
from .exporters.markdown import render_markdown_report


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "agent.config.json"


def log_step(message: str) -> None:
    print(f"[radar] {message}", flush=True)


def blocked_source_reasons(source_name: str, payload: dict[str, Any]) -> list[str]:
    if source_name == "Meta Ads Library":
        results = payload.get("results", [])
        ads = payload.get("ads", [])
        if not results:
            return ["a coleta nao retornou nenhuma query processada"]
        error_count = sum(1 for item in results if item.get("status") == "error")
        zero_card_count = sum(1 for item in results if not item.get("cards"))
        reasons: list[str] = []
        if error_count == len(results):
            reasons.append("todas as queries retornaram erro")
        if zero_card_count == len(results):
            reasons.append("nenhuma query retornou cards de anuncio")
        if error_count:
            reasons.append(f"{error_count}/{len(results)} queries tiveram erro")
        return reasons
    if source_name == "Reddit":
        signals = payload.get("signals", [])
        errors = payload.get("errors", [])
        if errors and not signals:
            return [f"{len(errors)} buscas falharam e nenhum post foi extraido"]
        if len(errors) >= max(3, len(signals) * 2):
            return [f"muitas buscas falharam ({len(errors)} erros para {len(signals)} sinais)"]
    if source_name == "Google Trends":
        signals = payload.get("signals", [])
        if not signals:
            return ["nenhuma trend foi coletada"]
    return []


def ask_blocked_source_decision(source_name: str, reasons: list[str], policy: str) -> str:
    log_step(f"ATENCAO: fonte bloqueada ou suspeita: {source_name}")
    for reason in reasons:
        log_step(f"- motivo: {reason}")
    log_step("sugestoes: tentar navegador visivel/login, reduzir queries, usar fixture/cookies, ou abortar e ajustar a fonte")

    if policy == "continue":
        log_step("politica continue: seguindo com a lacuna registrada")
        return "continue"
    if policy == "stop":
        raise SystemExit(f"Fonte bloqueada: {source_name}. Ajuste a fonte ou rode com --blocked-source-policy ask/continue.")

    if not sys.stdin.isatty():
        raise SystemExit(
            f"Fonte bloqueada: {source_name}. Terminal nao interativo; rode novamente e escolha, "
            "ou use --blocked-source-policy continue para seguir assumindo a lacuna."
        )

    print("")
    print(f"[radar] {source_name} travou ou veio vazio. O que fazer?")
    print("[r] tentar de novo com navegador visivel")
    print("[c] continuar a rodada marcando essa lacuna")
    print("[a] abortar para voce ajustar login/cookies/queries")
    while True:
        choice = input("[radar] escolha r/c/a: ").strip().lower()
        if choice in {"r", "retry", "tentar"}:
            return "retry-visible"
        if choice in {"c", "continue", "continuar"}:
            return "continue"
        if choice in {"a", "abort", "abortar"}:
            raise SystemExit(f"Rodada abortada por bloqueio em {source_name}.")
        print("[radar] escolha invalida. Use r, c ou a.")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def command_run(args: argparse.Namespace) -> None:
    log_step(f"lendo configuracao: {args.config}")
    config = read_json(Path(args.config))
    log_step(f"lendo sinais/teses: {args.input}")
    input_data = read_json(Path(args.input))
    log_step(
        "pontuando oportunidades: "
        f"{len(input_data.get('signals', []))} sinais, "
        f"{len(input_data.get('opportunity_hypotheses', []))} hipoteses"
    )
    result = run_opportunity_research(input_data, config)
    log_step(
        "resultado da rodada: "
        f"{result['opportunity_count']} oportunidades, "
        f"{result.get('promising_count', 0)}/{result.get('min_promising_target', 5)} promissoras, "
        f"status {result.get('round_status')}"
    )
    write_json(Path(args.json_out), result)
    log_step(f"JSON salvo: {args.json_out}")
    write_text(Path(args.out), render_markdown_report(result))
    log_step(f"relatorio markdown salvo: {args.out}")
    if args.kanban_out:
        write_text(Path(args.kanban_out), render_html_kanban(result))
        log_step(f"kanban HTML salvo: {args.kanban_out}")
    if args.war_room_out:
        write_text(Path(args.war_room_out), render_html_war_room(result))
        log_step(f"war room HTML salvo: {args.war_room_out}")
    top = result["opportunities"][0] if result["opportunities"] else None
    print(f"OK report: {args.out}")
    print(f"OK json: {args.json_out}")
    if args.kanban_out:
        print(f"OK kanban: {args.kanban_out}")
    if args.war_room_out:
        print(f"OK war room: {args.war_room_out}")
    if top:
        print(f"Top: {top['title']} ({top['scores']['decision']}, score {top['scores']['overall']})")


def command_collect_trends(args: argparse.Namespace) -> None:
    log_step(f"coletando Google Trends RSS: geo={args.geo}")
    result = collect_google_trends_daily(args.geo)
    write_json(Path(args.out), result)
    print(f"OK trends: {args.out}")
    print(f"Signals: {len(result['signals'])}")


def _match_trends_to_hypotheses(seed: dict[str, Any], trends: dict[str, Any]) -> list[dict[str, Any]]:
    hypotheses = seed.get("opportunity_hypotheses", [])
    matched: list[dict[str, Any]] = []
    for trend in trends.get("signals", []):
        trend_text = " ".join([str(trend.get("title", "")), str(trend.get("summary", ""))]).lower()
        for hypothesis in hypotheses:
            terms = [
                str(hypothesis.get("title", "")),
                str(hypothesis.get("promise", "")),
                *[str(tag) for tag in hypothesis.get("tags", [])],
                *[str(term) for term in hypothesis.get("pain_terms", [])],
                *[str(term) for term in hypothesis.get("offer_terms", [])],
            ]
            tokens = {
                token
                for term in terms
                for token in term.lower().replace("/", " ").replace("-", " ").split()
                if len(token) >= 4
            }
            hits = [token for token in tokens if token in trend_text]
            if len(hits) >= 2:
                enriched = {**trend}
                enriched["cluster_key"] = hypothesis["cluster_key"]
                enriched["id"] = f"{trend.get('id')}-{hypothesis['cluster_key']}"
                enriched["summary"] = f"{trend.get('summary', '')} | matched_terms={hits[:6]}"
                enriched["tags"] = [*trend.get("tags", []), "matched_trend"]
                matched.append(enriched)
                break
    return matched


def command_collect_meta_ads(args: argparse.Namespace) -> None:
    mode = f"fixture {args.from_fixture}" if args.from_fixture else "coleta real Playwright"
    log_step(
        "iniciando Meta Ads Library: "
        f"{mode}, queries={args.queries_file}, pais={args.country}, max_ads={args.max_ads}, "
        f"scrolls={args.scroll_rounds}, headless={args.headless}"
    )
    command = [
        "node",
        "scripts/meta_ads_playwright.mjs",
        "--queries-file",
        args.queries_file,
        "--out",
        args.out,
        "--country",
        args.country,
        "--max-ads",
        str(args.max_ads),
        "--scroll-rounds",
        str(args.scroll_rounds),
        "--headless",
        str(args.headless).lower(),
    ]
    if args.from_fixture:
        command.extend(["--from-fixture", args.from_fixture])
    if args.snapshot_dir:
        command.extend(["--snapshot-dir", args.snapshot_dir])
    if args.browser_path:
        command.extend(["--browser-path", args.browser_path])

    subprocess.run(command, check=True)
    log_step(f"Meta Ads finalizado: bruto salvo em {args.out}")


def _write_outputs(args: argparse.Namespace, result: dict[str, Any]) -> None:
    write_json(Path(args.json_out), result)
    log_step(f"JSON salvo: {args.json_out}")
    write_text(Path(args.report_out), render_markdown_report(result))
    log_step(f"markdown salvo: {args.report_out}")
    write_text(Path(args.kanban_out), render_html_kanban(result))
    log_step(f"kanban salvo: {args.kanban_out}")
    write_text(Path(args.war_room_out), render_html_war_room(result))
    log_step(f"war room salvo: {args.war_room_out}")


def command_round_with_meta_ads(args: argparse.Namespace) -> None:
    log_step("rodada completa com Meta Ads iniciada")
    log_step("etapa 1/6: coletar anuncios e sinais de distribuicao")
    while True:
        command_collect_meta_ads(args)
        meta_ads_probe = read_json(Path(args.out))
        reasons = blocked_source_reasons("Meta Ads Library", meta_ads_probe)
        if not reasons:
            break
        decision = ask_blocked_source_decision("Meta Ads Library", reasons, args.blocked_source_policy)
        if decision == "retry-visible":
            args.headless = "false"
            log_step("repetindo coleta da Meta Ads Library com navegador visivel")
            continue
        break
    log_step(f"etapa 2/6: lendo seed base: {args.seed}")
    seed = read_json(Path(args.seed))
    log_step(f"etapa 3/6: lendo coleta Meta Ads: {args.out}")
    meta_ads = read_json(Path(args.out))
    log_step(
        "coleta Meta Ads resumida: "
        f"{len(meta_ads.get('ads', []))} ads, "
        f"{len(meta_ads.get('signals', []))} sinais, "
        f"{len(meta_ads.get('global_scale_groups', []))} grupos globais de escala/duplicacao"
    )
    seed["signals"] = [*seed.get("signals", []), *meta_ads.get("signals", [])]
    seed["run_name"] = args.run_name or f"{seed.get('run_name', 'round')}-with-meta-ads"
    write_json(Path(args.merged_seed_out), seed)
    log_step(
        f"etapa 4/6: seed mesclada salva em {args.merged_seed_out} "
        f"com {len(seed.get('signals', []))} sinais totais"
    )

    log_step(f"etapa 5/6: pontuando oportunidades com config {args.config}")
    config = read_json(Path(args.config))
    result = run_opportunity_research(seed, config)
    log_step(
        "score concluido: "
        f"{result['opportunity_count']} oportunidades, "
        f"{result.get('promising_count', 0)}/{result.get('min_promising_target', 5)} promissoras, "
        f"status {result.get('round_status')}"
    )
    log_step("etapa 6/6: gerando arquivos de saida")
    _write_outputs(args, result)
    top = result["opportunities"][0] if result["opportunities"] else None
    print(f"OK merged seed: {args.merged_seed_out}")
    print(f"OK report: {args.report_out}")
    print(f"OK json: {args.json_out}")
    print(f"OK kanban: {args.kanban_out}")
    print(f"OK war room: {args.war_room_out}")
    if top:
        print(f"Top: {top['title']} ({top['scores']['decision']}, score {top['scores']['overall']})")


def command_super_run(args: argparse.Namespace) -> None:
    log_step("SUPER-RUN iniciado: seed + Meta Ads + Reddit + Google Trends + scoring V2")
    seed = read_json(Path(args.seed))
    seed_signals = list(seed.get("signals", []))
    source_notes: list[str] = []

    log_step("fonte 1/3: Meta Ads Library")
    command_collect_meta_ads(args)
    meta_ads = read_json(Path(args.out))
    reasons = blocked_source_reasons("Meta Ads Library", meta_ads)
    if reasons:
        decision = ask_blocked_source_decision("Meta Ads Library", reasons, args.blocked_source_policy)
        if decision == "retry-visible":
            args.headless = "false"
            command_collect_meta_ads(args)
            meta_ads = read_json(Path(args.out))
    seed_signals.extend(meta_ads.get("signals", []))
    source_notes.append(f"Meta Ads: {len(meta_ads.get('ads', []))} ads, {len(meta_ads.get('signals', []))} sinais")

    log_step("fonte 2/3: Reddit")
    try:
        reddit_config = read_json(Path(args.reddit_queries_file))
        reddit = collect_reddit_search(reddit_config)
        write_json(Path(args.reddit_out), reddit)
        reddit_reasons = blocked_source_reasons("Reddit", reddit)
        if reddit_reasons:
            ask_blocked_source_decision("Reddit", reddit_reasons, args.blocked_source_policy)
        seed_signals.extend(reddit.get("signals", []))
        source_notes.append(f"Reddit: {len(reddit.get('signals', []))} sinais, {len(reddit.get('errors', []))} erros")
        log_step(source_notes[-1])
    except Exception as error:  # noqa: BLE001 - source must not silently disappear.
        source_notes.append(f"Reddit falhou: {error}")
        log_step(f"ATENCAO: Reddit falhou: {error}")
        if args.blocked_source_policy == "stop":
            raise

    log_step("fonte 3/3: Google Trends")
    try:
        trends = collect_google_trends_daily(args.trends_geo)
        write_json(Path(args.trends_out), trends)
        trend_reasons = blocked_source_reasons("Google Trends", trends)
        if trend_reasons:
            ask_blocked_source_decision("Google Trends", trend_reasons, args.blocked_source_policy)
        matched_trends = _match_trends_to_hypotheses(seed, trends)
        seed_signals.extend(matched_trends)
        source_notes.append(f"Google Trends: {len(trends.get('signals', []))} trends, {len(matched_trends)} vinculadas")
        log_step(source_notes[-1])
    except Exception as error:  # noqa: BLE001
        source_notes.append(f"Google Trends falhou: {error}")
        log_step(f"ATENCAO: Google Trends falhou: {error}")
        if args.blocked_source_policy == "stop":
            raise

    seed["signals"] = seed_signals
    seed["run_name"] = args.run_name or f"{seed.get('run_name', 'round')}-super-run-v2"
    seed["source_notes"] = source_notes
    write_json(Path(args.merged_seed_out), seed)
    log_step(f"seed super-run salva: {args.merged_seed_out} com {len(seed_signals)} sinais")

    config = read_json(Path(args.config))
    result = run_opportunity_research(seed, config)
    log_step(
        "score V2 concluido: "
        f"{result['opportunity_count']} oportunidades, "
        f"{result.get('promising_count', 0)}/{result.get('min_promising_target', 5)} promissoras, "
        f"status {result.get('round_status')}"
    )
    _write_outputs(args, result)
    top = result["opportunities"][0] if result["opportunities"] else None
    if top:
        print(f"Top: {top['title']} ({top['scores']['decision']}, score {top['scores']['overall']})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gotham-radar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Pontua oportunidades a partir de sinais JSON.")
    run.add_argument("--input", default="data/seeds/first-test-signals.json")
    run.add_argument("--config", default=str(DEFAULT_CONFIG))
    run.add_argument("--out", default="data/reports/first-test.md")
    run.add_argument("--json-out", default="data/opportunities/first-test.json")
    run.add_argument("--kanban-out", default="data/reports/first-test-kanban.html")
    run.add_argument("--war-room-out", default="data/reports/first-test-war-room.html")
    run.set_defaults(func=command_run)

    trends = subparsers.add_parser("collect-trends", help="Coleta Google Trends RSS diario.")
    trends.add_argument("--geo", default="BR")
    trends.add_argument("--out", default="data/raw/google-trends-br.json")
    trends.set_defaults(func=command_collect_trends)

    meta = subparsers.add_parser("collect-meta-ads", help="Coleta Meta Ads Library via Playwright/Edge.")
    meta.add_argument("--queries-file", default="data/meta_ads_queries.json")
    meta.add_argument("--country", default="BR")
    meta.add_argument("--out", default="data/raw/meta-ads-live.json")
    meta.add_argument("--max-ads", type=int, default=12)
    meta.add_argument("--scroll-rounds", type=int, default=5)
    meta.add_argument("--headless", default="true")
    meta.add_argument("--snapshot-dir", default="data/raw/meta_ads_snapshots")
    meta.add_argument("--browser-path", default="")
    meta.add_argument("--from-fixture", default="")
    meta.set_defaults(func=command_collect_meta_ads)

    meta_round = subparsers.add_parser("round-with-meta-ads", help="Coleta Meta Ads, mistura na seed e gera Kanban.")
    meta_round.add_argument("--seed", default="data/seeds/live-round-2026-05-13.json")
    meta_round.add_argument("--queries-file", default="data/meta_ads_queries.json")
    meta_round.add_argument("--country", default="BR")
    meta_round.add_argument("--out", default="data/raw/meta-ads-live.json")
    meta_round.add_argument("--max-ads", type=int, default=12)
    meta_round.add_argument("--scroll-rounds", type=int, default=5)
    meta_round.add_argument("--headless", default="true")
    meta_round.add_argument("--snapshot-dir", default="data/raw/meta_ads_snapshots")
    meta_round.add_argument("--browser-path", default="")
    meta_round.add_argument("--from-fixture", default="")
    meta_round.add_argument("--merged-seed-out", default="data/seeds/live-round-with-meta-ads.json")
    meta_round.add_argument("--config", default=str(DEFAULT_CONFIG))
    meta_round.add_argument("--report-out", default="data/reports/live-round-with-meta-ads.md")
    meta_round.add_argument("--json-out", default="data/opportunities/live-round-with-meta-ads.json")
    meta_round.add_argument("--kanban-out", default="data/reports/live-round-with-meta-ads-kanban.html")
    meta_round.add_argument("--war-room-out", default="data/reports/live-round-with-meta-ads-war-room.html")
    meta_round.add_argument(
        "--blocked-source-policy",
        choices=["ask", "continue", "stop"],
        default="ask",
        help="O que fazer quando uma fonte critica travar ou vier vazia.",
    )
    meta_round.add_argument("--run-name", default="")
    meta_round.set_defaults(func=command_round_with_meta_ads)

    super_run = subparsers.add_parser("super-run", help="Orquestra seed + Meta Ads + Reddit + Trends e gera War Room V2.")
    super_run.add_argument("--seed", default="data/seeds/live-round-2026-05-13.json")
    super_run.add_argument("--queries-file", default="data/meta_ads_queries.json")
    super_run.add_argument("--reddit-queries-file", default="data/reddit_queries.json")
    super_run.add_argument("--country", default="BR")
    super_run.add_argument("--trends-geo", default="BR")
    super_run.add_argument("--out", default="data/raw/super-run-meta-ads.json")
    super_run.add_argument("--reddit-out", default="data/raw/super-run-reddit.json")
    super_run.add_argument("--trends-out", default="data/raw/super-run-google-trends.json")
    super_run.add_argument("--max-ads", type=int, default=12)
    super_run.add_argument("--scroll-rounds", type=int, default=5)
    super_run.add_argument("--headless", default="true")
    super_run.add_argument("--snapshot-dir", default="data/raw/meta_ads_snapshots")
    super_run.add_argument("--browser-path", default="")
    super_run.add_argument("--from-fixture", default="")
    super_run.add_argument("--merged-seed-out", default="data/seeds/super-run-v2-seed.json")
    super_run.add_argument("--config", default=str(DEFAULT_CONFIG))
    super_run.add_argument("--report-out", default="data/reports/super-run-v2.md")
    super_run.add_argument("--json-out", default="data/opportunities/super-run-v2.json")
    super_run.add_argument("--kanban-out", default="data/reports/super-run-v2-kanban.html")
    super_run.add_argument("--war-room-out", default="data/reports/super-run-v2-war-room.html")
    super_run.add_argument(
        "--blocked-source-policy",
        choices=["ask", "continue", "stop"],
        default="ask",
        help="O que fazer quando uma fonte critica travar ou vier vazia.",
    )
    super_run.add_argument("--run-name", default="")
    super_run.set_defaults(func=command_super_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
