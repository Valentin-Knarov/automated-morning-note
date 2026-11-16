"""Lecture de la configuration (watchlist.toml) et univers fictif du mode démo."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    category: str = "Watchlist"


@dataclass(frozen=True)
class Config:
    title: str
    author: str
    markets: list[Instrument]
    watchlist: list[Instrument]
    max_news_per_stock: int = 2
    volume_alert: float = 2.0
    move_alert_sigma: float = 2.0
    demo: bool = field(default=False)

    @property
    def instruments(self) -> list[Instrument]:
        return self.markets + self.watchlist


def load_config(path: str | Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    note = raw.get("note", {})
    markets = [Instrument(m["symbol"], m["name"], m.get("category", "Indices")) for m in raw.get("markets", [])]
    watch = [Instrument(w["symbol"], w["name"], "Watchlist") for w in raw.get("watchlist", [])]
    if not watch:
        raise ValueError("La watchlist est vide : ajoute au moins un titre dans watchlist.toml.")
    return Config(
        title=note.get("title", "Morning note"),
        author=note.get("author", ""),
        markets=markets,
        watchlist=watch,
        max_news_per_stock=int(note.get("max_news_per_stock", 2)),
        volume_alert=float(note.get("volume_alert", 2.0)),
        move_alert_sigma=float(note.get("move_alert_sigma", 2.0)),
    )


def demo_config() -> Config:
    """Configuration du mode démo : instruments fictifs, pour ne pas prêter de faux cours à de vraies sociétés."""
    markets = [
        Instrument("DEMO-IDX-FR", "Indice France (démo)", "Indices"),
        Instrument("DEMO-IDX-EU", "Indice Europe (démo)", "Indices"),
        Instrument("DEMO-IDX-US", "Indice États-Unis (démo)", "Indices"),
        Instrument("DEMO-VOL", "Indice de volatilité (démo)", "Volatilité"),
        Instrument("DEMO-FX", "EUR/USD (démo)", "Change"),
        Instrument("DEMO-OIL", "Pétrole (démo)", "Matières premières"),
        Instrument("DEMO-RATE", "Taux 10 ans (démo)", "Taux"),
    ]
    watch = [Instrument(f"DEMO-{c}", f"Société {c} (démo)", "Watchlist") for c in "ABCDEFGHIJ"]
    return Config("Morning note — démonstration", "", markets, watch, demo=True)
