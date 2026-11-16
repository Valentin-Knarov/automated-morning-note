"""Génère la morning note : python -m morning_note [--demo] [--config watchlist.toml] [--send]"""

from __future__ import annotations

import argparse
from pathlib import Path

from morning_note import analytics
from morning_note.config import demo_config, load_config
from morning_note.data import load_yahoo, simulate
from morning_note.render import NoteContent, to_html, to_markdown


def build_note(cfg, data, commentary: str = "", intraday: bool = False) -> NoteContent:
    markets, watch = analytics.build_tables(cfg, data)
    gainers, losers = analytics.top_movers(watch)
    return NoteContent(
        title=cfg.title, author=cfg.author, as_of=data.as_of, demo=cfg.demo,
        headline=analytics.headline(markets, watch), markets=markets, watch=watch,
        gainers=gainers, losers=losers, alerts=analytics.alerts(cfg, watch, data), news=data.news,
        commentary=commentary, intraday=intraday,
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Morning note automatisée")
    ap.add_argument("--demo", action="store_true", help="instruments fictifs et données simulées (sans connexion)")
    ap.add_argument("--config", type=Path, default=Path("watchlist.toml"), help="fichier de configuration")
    ap.add_argument("--out", type=Path, default=Path("output"), help="dossier de sortie")
    ap.add_argument("--no-news", action="store_true", help="ne pas récupérer les actualités et dates de résultats")
    ap.add_argument("--commentary", default="", help="commentaire du desk à insérer en tête de note")
    ap.add_argument("--send", action="store_true", help="envoyer la note par e-mail (variables SMTP_*)")
    ap.add_argument("--intraday", action="store_true",
                    help="garder les cours de la séance en cours (point de marché en journée) au lieu des clôtures")
    args = ap.parse_args(argv)

    cfg = demo_config() if args.demo else load_config(args.config)
    data = simulate(cfg) if args.demo else load_yahoo(cfg, with_news=not args.no_news, intraday=args.intraday)
    missing = [i.name for i in cfg.instruments if i.symbol not in data.prices]
    if missing:
        print(f"Sans données : {', '.join(missing)}")

    note = build_note(cfg, data, args.commentary, intraday=args.intraday)
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"morning_{data.as_of:%Y-%m-%d}"
    html, md = to_html(note), to_markdown(note)
    (args.out / f"{stem}.html").write_text(html, encoding="utf-8")
    (args.out / f"{stem}.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"Note écrite : {args.out / (stem + '.html')}")

    if args.send:
        from morning_note.send import send_email

        to = send_email(f"{cfg.title} — {data.as_of:%d/%m/%Y}", html, md)
        print(f"Envoyée à : {', '.join(to)}")


if __name__ == "__main__":
    main()
