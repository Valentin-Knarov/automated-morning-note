import numpy as np
import pandas as pd
import pytest

from morning_note import analytics
from morning_note.__main__ import build_note, main
from morning_note.config import Instrument, demo_config, load_config
from morning_note.data import _parse_news, simulate
from morning_note.fmt import bp, num, pct
from morning_note.render import to_html, to_markdown


@pytest.fixture(scope="module")
def demo():
    cfg = demo_config()
    return cfg, simulate(cfg)


def _series(values, volumes=None):
    idx = pd.bdate_range(end="2026-11-13", periods=len(values))
    v = volumes if volumes is not None else np.full(len(values), 1000.0)
    return pd.DataFrame({"open": values, "high": values, "low": values, "close": values, "volume": v}, index=idx)


def test_config_file_loads():
    cfg = load_config("watchlist.toml")
    assert len(cfg.watchlist) >= 5 and any(m.category == "Taux" for m in cfg.markets)


def test_changes_and_rates_in_bp():
    df = _series(np.r_[np.full(300, 4.00), 4.10])
    row = analytics.instrument_stats(Instrument("^TNX", "Taux", "Taux"), df)
    assert row["chg_1d_bp"] == pytest.approx(10.0)
    assert row["chg_1d"] == pytest.approx(0.025)


def test_new_high_and_volume_alert():
    prices = np.r_[np.linspace(100, 110, 300), 115.0]
    vols = np.r_[np.full(300, 1000.0), 3500.0]
    row = analytics.instrument_stats(Instrument("X", "X"), _series(prices, vols))
    assert row["new_high"] and not row["new_low"]
    assert row["volume_ratio"] == pytest.approx(3.5)


def test_rsi_bounds():
    up = pd.Series(np.linspace(10, 20, 50))
    assert analytics.rsi(up) == 100.0
    assert 0 <= analytics.rsi(pd.Series(np.sin(np.arange(60)) + 10)) <= 100


def test_alerts_detect_simulated_events(demo):
    cfg, data = demo
    _, watch = analytics.build_tables(cfg, data)
    kinds = {a["type"] for a in analytics.alerts(cfg, watch, data)}
    assert {"Mouvement anormal", "Volume anormal"} <= kinds


def test_top_movers_order(demo):
    cfg, data = demo
    _, watch = analytics.build_tables(cfg, data)
    g, l = analytics.top_movers(watch)
    assert g["chg_1d"].is_monotonic_decreasing and l["chg_1d"].is_monotonic_increasing
    assert g["chg_1d"].iloc[0] == watch["chg_1d"].max()


def test_french_formats():
    assert pct(0.0123) == "+1,2 %" and pct(-0.00004) == "0,0 %"
    assert num(12345.678) == "12 345,68" and bp(-7.2) == "-7 pb"


def test_render_html_and_markdown(demo):
    cfg, data = demo
    note = build_note(cfg, data, commentary="Test de commentaire.")
    html, md = to_html(note), to_markdown(note)
    assert "Marchés" in html and "Test de commentaire." in html and "Démonstration" in html
    assert md.startswith("# Morning note")


def test_news_parsing_both_formats():
    old = [{"title": "A", "publisher": "P", "link": "http://x", "providerPublishTime": 1_700_000_000}]
    new = [{"content": {"title": "B", "provider": {"displayName": "Q"}, "canonicalUrl": {"url": "http://y"},
                        "pubDate": "2026-11-13T07:00:00Z"}}]
    assert _parse_news(old, 2)[0].publisher == "P"
    assert _parse_news(new, 2)[0].link == "http://y"


def test_cli_demo(tmp_path, capsys):
    main(["--demo", "--out", str(tmp_path)])
    assert list(tmp_path.glob("morning_*.html")) and list(tmp_path.glob("morning_*.md"))
