"""Récupération des données : Yahoo Finance (cours, actualités, dates de résultats) ou simulation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from morning_note.config import Config

COLUMNS = ["open", "high", "low", "close", "volume"]
PARIS = ZoneInfo("Europe/Paris")

# Heure de Paris à partir de laquelle la séance du jour est considérée comme close (marge après le fixing).
EUROPE_CLOSE = time(17, 45)
US_CLOSE = time(22, 15)
ASIA_CLOSE = time(8, 0)
EUROPE_SUFFIXES = (".PA", ".AS", ".BR", ".LS", ".DE", ".MI", ".MC", ".L", ".SW")
EUROPE_INDICES = {"^FCHI", "^STOXX50E", "^GDAXI", "^FTSE", "^IBEX", "^AEX", "^SBF120"}
ASIA_INDICES = {"^N225", "^HSI", "000001.SS", "^AXJO"}


@dataclass(frozen=True)
class NewsItem:
    title: str
    publisher: str
    link: str
    published: datetime | None


@dataclass
class MarketData:
    prices: dict[str, pd.DataFrame]  # symbol -> OHLCV journalier
    news: dict[str, list[NewsItem]]
    earnings: dict[str, pd.Timestamp]  # symbol -> prochaine date de résultats
    as_of: pd.Timestamp


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=str.lower)
    df = df[[c for c in COLUMNS if c in df.columns]].dropna(subset=["close"])
    if "volume" not in df:
        df["volume"] = 0.0
    df.index = pd.to_datetime(df.index).tz_localize(None) if getattr(df.index, "tz", None) else pd.to_datetime(df.index)
    return df


def _parse_news(raw: list[dict], limit: int) -> list[NewsItem]:
    """Les champs renvoyés par Yahoo ont changé selon les versions : on gère les deux formats."""
    items = []
    for n in raw[:limit]:
        c = n.get("content", n)
        title = c.get("title")
        if not title:
            continue
        publisher = (c.get("provider") or {}).get("displayName") or c.get("publisher", "")
        link = ((c.get("canonicalUrl") or {}).get("url")) or c.get("link", "")
        ts = c.get("pubDate") or c.get("providerPublishTime")
        published = None
        if isinstance(ts, (int, float)):
            published = datetime.fromtimestamp(ts)
        elif isinstance(ts, str):
            published = pd.to_datetime(ts).to_pydatetime().replace(tzinfo=None)
        items.append(NewsItem(title, publisher, link, published))
    return items


def session_close(symbol: str) -> time | None:
    """Heure de clôture (heure de Paris) du marché de l'instrument ; None pour un marché continu.

    Change (``=X``) et contrats à terme (``=F``) cotent presque 24 h sur 24 : leur dernier prix
    est conservé tel quel, c'est l'usage dans une morning note.
    """
    if symbol.endswith(("=X", "=F")):
        return None
    if symbol in EUROPE_INDICES or symbol.upper().endswith(EUROPE_SUFFIXES):
        return EUROPE_CLOSE
    if symbol in ASIA_INDICES or symbol.upper().endswith((".T", ".HK")):
        return ASIA_CLOSE
    return US_CLOSE  # indices et actions américains, VIX, taux US


def drop_unfinished_session(df: pd.DataFrame, symbol: str, now: datetime | None = None) -> pd.DataFrame:
    """Retire la barre du jour si la séance n'est pas encore close.

    Lancée en cours de séance, Yahoo renvoie une barre « du jour » avec le dernier cours, pas une
    clôture : la note la présenterait à tort comme une clôture. On garde alors la séance précédente.
    """
    now = now or datetime.now(PARIS)
    close = session_close(symbol)
    if close is None or df.empty:
        return df
    if df.index[-1].date() == now.date() and now.time() < close:
        return df.iloc[:-1]
    return df


def load_yahoo(cfg: Config, period: str = "1y", with_news: bool = True, intraday: bool = False) -> MarketData:
    """Cours journaliers, actualités et dates de résultats.

    intraday : si vrai, garde les cours de la séance en cours (point de marché en journée) ;
    sinon, seules les séances closes sont utilisées.
    """
    import yfinance as yf

    symbols = [i.symbol for i in cfg.instruments]
    raw = yf.download(symbols, period=period, interval="1d", auto_adjust=False, group_by="ticker", progress=False)
    prices = {}
    for s in symbols:
        try:
            df = raw[s] if isinstance(raw.columns, pd.MultiIndex) else raw
            df = _clean(df)
            if not intraday:
                df = drop_unfinished_session(df, s)
            if len(df) >= 2:
                prices[s] = df
        except KeyError:
            continue
    if not prices:
        raise ValueError("Aucune donnée Yahoo : vérifie la connexion internet et les tickers de watchlist.toml.")

    news, earnings = {}, {}
    if with_news:
        for inst in cfg.watchlist:
            t = yf.Ticker(inst.symbol)
            try:
                news[inst.symbol] = _parse_news(t.news or [], cfg.max_news_per_stock)
            except Exception:  # les actualités sont un bonus : on n'interrompt pas la note
                news[inst.symbol] = []
            try:
                dates = t.get_earnings_dates(limit=4)
                if dates is not None and not dates.empty:
                    idx = pd.to_datetime(dates.index).tz_localize(None)
                    future = idx[idx >= pd.Timestamp.today().normalize()]
                    if len(future):
                        earnings[inst.symbol] = future.min()
            except Exception:
                pass
    # Date de référence : dernière séance close de la watchlist (le change peut dater du jour même).
    watch_dates = [prices[i.symbol].index[-1] for i in cfg.watchlist if i.symbol in prices]
    as_of = max(watch_dates or [df.index[-1] for df in prices.values()])
    return MarketData(prices, news, earnings, as_of)


def simulate(cfg: Config, n_days: int = 260, seed: int = 7) -> MarketData:
    """Données simulées pour le mode démo et les tests (quelques mouvements et volumes anormaux inclus)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp("2026-11-13"), periods=n_days)
    prices, news, earnings = {}, {}, {}
    levels = {"Indices": 7500, "Volatilité": 17, "Change": 1.08, "Matières premières": 78, "Taux": 4.2}
    vols = {"Indices": 0.010, "Volatilité": 0.03, "Change": 0.004, "Matières premières": 0.018, "Taux": 0.015}
    for k, inst in enumerate(cfg.instruments):
        p0 = levels.get(inst.category, rng.uniform(20, 400))
        sigma = vols.get(inst.category, rng.uniform(0.012, 0.025))
        r = rng.normal(0.0002, sigma, n_days)
        if inst.category == "Watchlist" and k % 4 == 0:
            r[-1] = rng.choice([-1, 1]) * 3.2 * sigma  # mouvement anormal le dernier jour
        close = p0 * np.exp(np.cumsum(r))
        high = close * (1 + np.abs(rng.normal(0, sigma / 2, n_days)))
        low = close * (1 - np.abs(rng.normal(0, sigma / 2, n_days)))
        volume = rng.lognormal(13, 0.3, n_days) if inst.category in ("Indices", "Watchlist") else np.zeros(n_days)
        if inst.category == "Watchlist" and k % 3 == 0:
            volume[-1] *= 3  # volume anormal
        prices[inst.symbol] = pd.DataFrame(
            {"open": np.r_[close[0], close[:-1]], "high": np.maximum(high, close), "low": np.minimum(low, close),
             "close": close, "volume": volume}, index=dates)
    for i, inst in enumerate(cfg.watchlist):
        news[inst.symbol] = [NewsItem(f"Titre d'actualité fictif n°{j + 1} sur {inst.name}", "Source démo", "", None)
                             for j in range(i % 3)]
        if i % 4 == 1:
            earnings[inst.symbol] = dates[-1] + pd.Timedelta(days=int(1 + i))
    return MarketData(prices, news, earnings, dates[-1])
