"""Mise en forme de la note : HTML (prêt pour un e-mail, styles en ligne) et Markdown."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from jinja2 import Environment

from morning_note.analytics import RATE_CATEGORIES
from morning_note.fmt import bp, num, pct

GREEN, RED, GREY, NAVY = "#1a7f4b", "#c0392b", "#5c6b7a", "#1f4e79"
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


@dataclass
class NoteContent:
    title: str
    author: str
    as_of: pd.Timestamp
    demo: bool
    headline: list[str]
    markets: pd.DataFrame
    watch: pd.DataFrame
    gainers: pd.DataFrame
    losers: pd.DataFrame
    alerts: list[dict]
    news: dict
    commentary: str = ""
    intraday: bool = False


def date_fr(d: pd.Timestamp) -> str:
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def color(x: float) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)) or abs(x) < 0.0005:
        return GREY  # variation nulle à l'arrondi près : ni vert ni rouge
    return GREEN if x > 0 else RED


def market_change(r, horizon: str = "1d") -> str:
    """Variation affichée : en points de base pour les taux, en % sinon (horizon : 1d, 5d ou ytd)."""
    if r["category"] in RATE_CATEGORIES:
        return bp(r[f"chg_{horizon}_bp"])
    return pct(r[f"chg_{horizon}"])


_env = Environment(autoescape=True)
_env.filters.update(pct=pct, num=num, color=color)
_env.globals.update(market_change=market_change, NAVY=NAVY, GREY=GREY)

_HTML = _env.from_string("""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>{{ c.title }}</title></head>
<body style="margin:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#1d2733">
<div style="max-width:760px;margin:0 auto;background:#fff;padding:28px 32px">
<div style="border-bottom:3px solid {{ NAVY }};padding-bottom:10px">
<div style="font-size:22px;font-weight:bold;color:{{ NAVY }}">{{ c.title }}</div>
<div style="font-size:13px;color:{{ GREY }}">{{ date }} · {% if c.intraday %}cours en séance du {{ close_date }}{% else %}données à la clôture du {{ close_date }}{% endif %}{% if c.author %} · {{ c.author }}{% endif %}</div>
</div>
{% if c.demo %}<p style="background:#fff8e6;border-left:4px solid #f0a202;padding:8px 12px;font-size:13px">Démonstration : instruments fictifs et données simulées.</p>{% endif %}

<h3 style="color:{{ NAVY }};margin-bottom:6px">En bref</h3>
<ul style="margin-top:0;padding-left:18px;font-size:14px;line-height:1.5">{% for l in c.headline %}<li>{{ l }}</li>{% endfor %}</ul>
{% if c.commentary %}<p style="font-size:14px;line-height:1.5;background:#f4f7fa;padding:10px 12px"><b>Commentaire du desk.</b> {{ c.commentary }}</p>{% endif %}

<h3 style="color:{{ NAVY }};margin-bottom:6px">Marchés</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="background:{{ NAVY }};color:#fff"><th align="left" style="padding:6px">Instrument</th><th align="right" style="padding:6px">Dernier</th><th align="right" style="padding:6px">1 j</th><th align="right" style="padding:6px">5 j</th><th align="right" style="padding:6px">Depuis 1er janv.</th></tr>
{% for cat, rows in markets %}<tr><td colspan="5" style="padding:8px 6px 2px;font-weight:bold;color:{{ GREY }};font-size:12px">{{ cat }}</td></tr>
{% for r in rows %}<tr style="border-bottom:1px solid #e3e8ee"><td style="padding:5px 6px">{{ r.name }}</td><td align="right" style="padding:5px 6px">{{ r.last|num }}</td>
<td align="right" style="padding:5px 6px;color:{{ r.chg_1d|color }};font-weight:bold">{{ market_change(r) }}</td>
<td align="right" style="padding:5px 6px;color:{{ r.chg_5d|color }}">{{ market_change(r, "5d") }}</td><td align="right" style="padding:5px 6px;color:{{ r.chg_ytd|color }}">{{ market_change(r, "ytd") }}</td></tr>{% endfor %}{% endfor %}
</table>

<h3 style="color:{{ NAVY }};margin-bottom:6px">Watchlist — plus fortes variations</h3>
<table style="width:100%;font-size:13px"><tr><td valign="top" style="width:50%;padding-right:8px">
<b style="color:{{ '#1a7f4b' }}">Hausses</b><table style="width:100%;border-collapse:collapse">{% for _, r in c.gainers.iterrows() %}
<tr style="border-bottom:1px solid #e3e8ee"><td style="padding:4px">{{ r['name'] }}</td><td align="right" style="padding:4px;color:{{ r['chg_1d']|color }};font-weight:bold">{{ r['chg_1d']|pct }}</td></tr>{% endfor %}</table></td>
<td valign="top" style="width:50%;padding-left:8px"><b style="color:{{ '#c0392b' }}">Baisses</b><table style="width:100%;border-collapse:collapse">{% for _, r in c.losers.iterrows() %}
<tr style="border-bottom:1px solid #e3e8ee"><td style="padding:4px">{{ r['name'] }}</td><td align="right" style="padding:4px;color:{{ r['chg_1d']|color }};font-weight:bold">{{ r['chg_1d']|pct }}</td></tr>{% endfor %}</table></td></tr></table>

<h3 style="color:{{ NAVY }};margin-bottom:6px">Points d'attention</h3>
{% if c.alerts %}<table style="width:100%;border-collapse:collapse;font-size:13px">{% for a in c.alerts %}
<tr style="border-bottom:1px solid #e3e8ee"><td style="padding:5px 6px;width:30%"><b>{{ a.name }}</b></td><td style="padding:5px 6px;width:25%;color:{{ GREY }}">{{ a.type }}</td><td style="padding:5px 6px">{{ a.detail }}</td></tr>{% endfor %}</table>
{% else %}<p style="font-size:13px;color:{{ GREY }}">Aucun signal particulier sur la watchlist.</p>{% endif %}

{% if news %}<h3 style="color:{{ NAVY }};margin-bottom:6px">Actualités</h3>
<ul style="padding-left:18px;font-size:13px;line-height:1.5">{% for name, items in news %}{% for n in items %}
<li><b>{{ name }}</b> — {% if n.link %}<a href="{{ n.link }}" style="color:{{ NAVY }}">{{ n.title }}</a>{% else %}{{ n.title }}{% endif %}{% if n.publisher %} <span style="color:{{ GREY }}">({{ n.publisher }})</span>{% endif %}</li>{% endfor %}{% endfor %}</ul>{% endif %}

<h3 style="color:{{ NAVY }};margin-bottom:6px">Watchlist complète</h3>
<table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="background:{{ NAVY }};color:#fff"><th align="left" style="padding:5px">Valeur</th><th align="right" style="padding:5px">Cours</th><th align="right" style="padding:5px">1 j</th><th align="right" style="padding:5px">5 j</th><th align="right" style="padding:5px">1 mois</th><th align="right" style="padding:5px">Depuis 1er janv.</th><th align="right" style="padding:5px">Vol. / moy. 20 j</th><th align="right" style="padding:5px">Écart plus haut 52 s.</th><th align="right" style="padding:5px">RSI 14</th></tr>
{% for _, r in c.watch.iterrows() %}<tr style="border-bottom:1px solid #e3e8ee"><td style="padding:4px 5px">{{ r['name'] }}</td><td align="right" style="padding:4px 5px">{{ r['last']|num }}</td>
<td align="right" style="padding:4px 5px;color:{{ r['chg_1d']|color }};font-weight:bold">{{ r['chg_1d']|pct }}</td><td align="right" style="padding:4px 5px;color:{{ r['chg_5d']|color }}">{{ r['chg_5d']|pct }}</td>
<td align="right" style="padding:4px 5px;color:{{ r['chg_1m']|color }}">{{ r['chg_1m']|pct }}</td><td align="right" style="padding:4px 5px;color:{{ r['chg_ytd']|color }}">{{ r['chg_ytd']|pct }}</td>
<td align="right" style="padding:4px 5px">{{ r['volume_ratio']|num(1) }} ×</td><td align="right" style="padding:4px 5px">{{ r['dist_high']|pct }}</td><td align="right" style="padding:4px 5px">{{ r['rsi_14']|num(0) }}</td></tr>{% endfor %}
</table>
<p style="font-size:11px;color:{{ GREY }};margin-top:20px">Note générée automatiquement à partir de données publiques (Yahoo Finance). Document d'information, ne constitue pas un conseil en investissement.</p>
</div></body></html>""")


def _grouped_markets(markets: pd.DataFrame) -> list[tuple[str, list[dict]]]:
    order = ["Indices", "Volatilité", "Change", "Matières premières", "Taux"]
    cats = sorted(markets["category"].unique(), key=lambda c: order.index(c) if c in order else 99) if len(markets) else []
    return [(c, markets[markets["category"] == c].to_dict("records")) for c in cats]


def to_html(c: NoteContent) -> str:
    name_of = dict(zip(c.watch["symbol"], c.watch["name"])) if len(c.watch) else {}
    news = [(name_of.get(s, s), items) for s, items in c.news.items() if items]
    return _HTML.render(c=c, date=date_fr(pd.Timestamp.today()), close_date=c.as_of.strftime("%d/%m/%Y"),
                        markets=_grouped_markets(c.markets), news=news)


def to_markdown(c: NoteContent) -> str:
    """Version texte, pratique pour un chat ou un message court."""
    when = "Cours en séance du" if c.intraday else "Données à la clôture du"
    lines = [f"# {c.title}", f"_{when} {c.as_of.strftime('%d/%m/%Y')}_", ""]
    if c.demo:
        lines += ["> Démonstration : instruments fictifs et données simulées.", ""]
    lines += ["## En bref"] + [f"- {l}" for l in c.headline] + [""]
    if c.commentary:
        lines += [f"**Commentaire du desk.** {c.commentary}", ""]
    lines += ["## Marchés", "| Instrument | Dernier | 1 j | 5 j | Depuis 1er janv. |", "|---|---:|---:|---:|---:|"]
    for _, r in c.markets.iterrows():
        lines.append(f"| {r['name']} | {num(r['last'])} | {market_change(r)} | {market_change(r, '5d')} | {market_change(r, 'ytd')} |")
    lines += ["", "## Watchlist — plus fortes variations"]
    lines += [f"- ▲ {r['name']} {pct(r['chg_1d'])}" for _, r in c.gainers.iterrows()]
    lines += [f"- ▼ {r['name']} {pct(r['chg_1d'])}" for _, r in c.losers.iterrows()]
    lines += ["", "## Points d'attention"]
    lines += [f"- **{a['name']}** — {a['type']} : {a['detail']}" for a in c.alerts] or ["- Aucun signal particulier."]
    return "\n".join(lines) + "\n"
