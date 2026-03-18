import math

TIER_INACTIVE_MAX = 0.25
TIER_AT_RISK_MAX = 0.55


def recent_activity_score(snapshot) -> float:
    """
    Score 0.0–1.0 focused on recent activity.

    Components:
      - Recency  40%: days_since_last_any (0d → 1.0, 14d → 0.0, linear)
      - Volume   40%: raw_7d normalised   (7 battles/week → 1.0, capped)
      - Trend    20%: ratio current week vs previous week (normalised 0–1)

    Accepts ActivityProfile (dataclass) or dict with compatible fields.
    """
    if isinstance(snapshot, dict):
        recency_days = snapshot.get("days_since_last_any", float("inf"))
        raw_7d = int(snapshot.get("raw_7d", 0))
        raw_14d = int(snapshot.get("raw_14d", 0))
    else:
        recency_days = snapshot.days_since_last_any
        raw_7d = snapshot.raw_7d
        raw_14d = snapshot.raw_14d

    # Recency (last 14 days since any battle)
    if not math.isfinite(float(recency_days)):
        recency = 0.0
    else:
        recency = max(0.0, 1.0 - float(recency_days) / 14.0)

    # Volume (normalised to 7 battles/week)
    volume = min(raw_7d / 7.0, 1.0)

    # Trend: current week vs previous week
    prev_7d = max(0, raw_14d - raw_7d)
    trend_ratio = raw_7d / max(1, max(0, prev_7d))
    trend = min(trend_ratio, 2.0) / 2.0

    return round(0.4 * recency + 0.4 * volume + 0.2 * trend, 4)


def trend_arrow(trend_ratio: float | None) -> str:
    """Returns visual trend indicator."""
    if trend_ratio is None:
        return "·"
    if trend_ratio >= 1.2:
        return "↗"
    if trend_ratio >= 0.8:
        return "→"
    return "↘"
