"""Formats à la française : virgule décimale, espace des milliers, espace avant %."""

from __future__ import annotations

import math


def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def pct(x: float, digits: int = 1) -> str:
    """+0,8 % ; « 0,0 % » sans signe pour une variation arrondie à zéro."""
    if _isnan(x):
        return "–"
    if round(x * 100, digits) == 0:
        return f"{0:.{digits}f} %".replace(".", ",")
    return f"{x * 100:+.{digits}f} %".replace(".", ",")


def num(x: float, digits: int = 2) -> str:
    if _isnan(x):
        return "–"
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",")


def bp(x: float) -> str:
    if _isnan(x):
        return "–"
    return "0 pb" if round(x) == 0 else f"{x:+.0f} pb"
