"""
ephemeris_utils.py
Planet positions for ANY moment (not just "now"), using the same KP ayanamsa as chart_caster.
This is what makes backtesting and reproducible readings possible.
"""
import swisseph as swe
from datetime import datetime, timezone, timedelta

# Node convention. KP software differs; test_engine.py compares this with your
# transit_engine.get_live_planets() so you can see which one you were using.
NODE_MODE = "true"          # "true" or "mean"

_BODIES = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
}
_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def to_jd(dt):
    """timezone-aware (or naive-UTC) datetime -> Julian Day (UT)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60.0 + (dt.second + dt.microsecond / 1e6) / 3600.0)


def from_jd(jd):
    """Julian Day (UT) -> timezone-aware UTC datetime."""
    y, m, d, h = swe.revjul(jd)
    secs = round(h * 3600.0)
    base = datetime(y, m, d, tzinfo=timezone.utc)
    return base + timedelta(seconds=secs)


def planets_at(jd):
    """Returns (positions {planet: sidereal longitude}, retrogrades {planet: bool}) at Julian Day jd."""
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    positions, retro = {}, {}
    for name, body in _BODIES.items():
        xx = swe.calc_ut(jd, body, _FLAGS)[0]  # [0] works for both 2-tuple and 3-tuple returns
        positions[name] = xx[0] % 360.0
        retro[name] = xx[3] < 0
    node_body = swe.TRUE_NODE if NODE_MODE == "true" else swe.MEAN_NODE
    xx = swe.calc_ut(jd, node_body, _FLAGS)[0]  # [0] works for both 2-tuple and 3-tuple returns
    positions["Rahu"] = xx[0] % 360.0
    positions["Ketu"] = (xx[0] + 180.0) % 360.0
    retro["Rahu"] = False   # nodes are always retrograde in motion; not treated as a retro *flag* in KP judgment
    retro["Ketu"] = False
    return positions, retro