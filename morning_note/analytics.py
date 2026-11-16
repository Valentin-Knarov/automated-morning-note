"""Calculs de la note : variations, mouvements anormaux, volumes, plus hauts / plus bas 52 semaines.

Notations :
    P_t : cours de clôture de la dernière séance, P_{t-k} : cours k séances plus tôt
    r_t : rendement de la dernière séance, P_t / P_{t-1} − 1
    σ_20 : écart-type des rendements journaliers sur les 20 séances précédentes
    N_t : volume de la dernière séance, N̄_20 : volume moyen des 20 séances précédentes
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from morning_note.config import Config, Instrument
from morning_note.data import MarketData
from morning_note.fmt import bp, num, pct

RATE_CATEGORIES = {"Taux"}  # variations exprimées en points de base, pas en %


def rsi(close: pd.Series, n: int = 14) -> float:
    """RSI de Wilder sur n séances : 100 − 100 / (1 + RS), RS = moyenne des hausses / moyenne des baisses."""
    delta = close.diff().dropna()
    if len(delta) < n:
        return float("nan")
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    return 100.0 if loss == 0 else float(100 - 100 / (1 + gain / loss))


def _change(close: pd.Series, k: int) -> float:
    return float(close.iloc[-1] / close.iloc[-1 - k] - 1) if len(close) > k else float("nan")


def instrument_stats(inst: Instrument, df: pd.DataFrame) -> dict:
    c = df["close"]
    last, prev = float(c.iloc[-1]), float(c.iloc[-2])
    ret = c.pct_change().dropna()
    sigma20 = float(ret.iloc[-21:-1].std()) if len(ret) > 21 else float("nan")
    year_start = c[c.index < pd.Timestamp(c.index[-1].year, 1, 1)]
    ytd = float(last / year_start.iloc[-1] - 1) if len(year_start) else float("nan")
    window = c.iloc[-253:-1]  # 52 semaines, hors dernière séance
    vol = df["volume"]
    vol_avg = float(vol.iloc[-21:-1].mean()) if len(vol) > 21 else float("nan")
    row = {
        "symbol": inst.symbol, "name": inst.name, "category": inst.category,
        "last": last,
        "chg_1d": last / prev - 1,
        "chg_5d": _change(c, 5), "chg_1m": _change(c, 21), "chg_ytd": ytd,
        "z_1d": (last / prev - 1) / sigma20 if sigma20 and sigma20 > 0 else float("nan"),
        "volume": float(vol.iloc[-1]),
        "volume_ratio": float(vol.iloc[-1]) / vol_avg if vol_avg and vol_avg > 0 else float("nan"),
        "high_52w": float(window.max()) if len(window) else float("nan"),
        "low_52w": float(window.min()) if len(window) else float("nan"),
        "rsi_14": rsi(c),
        "date": c.index[-1],
    }
    row["new_high"] = bool(len(window) >= 200 and last > row["high_52w"])
    row["new_low"] = bool(len(window) >= 200 and last < row["low_52w"])
    row["dist_high"] = last / row["high_52w"] - 1 if row["high_52w"] else float("nan")
    if inst.category in RATE_CATEGORIES:  # taux cotés en % : variations en points de base
        row["chg_1d_bp"] = (last - prev) * 100
        row["chg_5d_bp"] = (last - float(c.iloc[-6])) * 100 if len(c) > 5 else float("nan")
        row["chg_ytd_bp"] = (last - float(year_start.iloc[-1])) * 100 if len(year_start) else float("nan")
    return row


def build_tables(cfg: Config, data: MarketData) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Renvoie (marchés, watchlist) : une ligne par instrument disponible."""
    def table(instruments):
        rows = [instrument_stats(i, data.prices[i.symbol]) for i in instruments if i.symbol in data.prices]
        return pd.DataFrame(rows)

    return table(cfg.markets), table(cfg.watchlist)


def alerts(cfg: Config, watch: pd.DataFrame, data: MarketData, horizon_days: int = 10) -> list[dict]:
    """Points d'attention : mouvement anormal, volume anormal, plus haut / bas 52 semaines, résultats à venir, RSI extrême."""
    out = []
    for _, r in watch.iterrows():
        if abs(r["z_1d"]) >= cfg.move_alert_sigma:
            out.append({"name": r["name"], "type": "Mouvement anormal",
                        "detail": f"{pct(r['chg_1d'])}, soit {num(abs(r['z_1d']), 1)} écarts-types journaliers"})
        if r["volume_ratio"] >= cfg.volume_alert:
            out.append({"name": r["name"], "type": "Volume anormal",
                        "detail": f"{num(r['volume_ratio'], 1)} × la moyenne des 20 séances"})
        if r["new_high"]:
            out.append({"name": r["name"], "type": "Plus haut 52 semaines", "detail": f"clôture à {num(r['last'])}"})
        if r["new_low"]:
            out.append({"name": r["name"], "type": "Plus bas 52 semaines", "detail": f"clôture à {num(r['last'])}"})
        if r["rsi_14"] >= 75 or r["rsi_14"] <= 25:
            out.append({"name": r["name"], "type": "RSI extrême",
                        "detail": f"RSI 14 j à {num(r['rsi_14'], 0)} ({'surachat' if r['rsi_14'] >= 75 else 'survente'})"})
        d = data.earnings.get(r["symbol"])
        if d is not None and 0 <= (d - data.as_of).days <= horizon_days:
            out.append({"name": r["name"], "type": "Résultats à venir", "detail": d.strftime("%d/%m/%Y")})
    return out


def headline(markets: pd.DataFrame, watch: pd.DataFrame) -> list[str]:
    """Résumé factuel en quelques phrases (pas d'opinion : le commentaire reste au sales)."""
    lines = []
    idx = markets[markets["category"] == "Indices"]
    if len(idx):
        parts = [f"{r['name']} {pct(r['chg_1d'])}" for _, r in idx.iterrows()]
        lines.append("Indices à la dernière clôture : " + ", ".join(parts) + ".")
    others = markets[markets["category"] != "Indices"]
    if len(others):
        parts = []
        for _, r in others.iterrows():
            if r["category"] in RATE_CATEGORIES:
                parts.append(f"{r['name']} {num(r['last'])} % ({bp(r['chg_1d_bp'])})")
            else:
                parts.append(f"{r['name']} {num(r['last'])} ({pct(r['chg_1d'])})")
        lines.append(" · ".join(parts) + ".")
    if len(watch):
        best, worst = watch.loc[watch["chg_1d"].idxmax()], watch.loc[watch["chg_1d"].idxmin()]
        breadth = int((watch["chg_1d"] > 0).sum())
        lines.append(
            f"Watchlist : {breadth} hausse(s) sur {len(watch)} valeurs ; meilleure performance {best['name']} "
            f"({pct(best['chg_1d'])}), plus forte baisse {worst['name']} ({pct(worst['chg_1d'])})."
        )
    return lines


def top_movers(watch: pd.DataFrame, n: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = watch.sort_values("chg_1d", ascending=False)
    return s.head(n), s.tail(n).iloc[::-1]
