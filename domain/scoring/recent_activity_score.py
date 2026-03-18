import math

TIER_INACTIVE_MAX = 0.25
TIER_AT_RISK_MAX = 0.55


def recent_activity_score(snapshot: dict) -> float:
    """
    Score 0.0–1.0 focado em atividade recente.

    Componentes:
      - Recência  40%: days_since_last_effective (0d → 1.0, 14d → 0.0, linear)
      - Volume    40%: weighted_7d normalizado   (7 bat/semana → 1.0, cap)
      - Tendência 20%: rácio semana atual vs semana anterior (normalizado 0–1)
    """
    # Recência
    recency_days = snapshot.get("days_since_last_effective", float("inf"))
    if not math.isfinite(float(recency_days)):
        recency = 0.0
    else:
        recency = max(0.0, 1.0 - float(recency_days) / 14.0)

    # Volume
    weighted_7d = float(snapshot.get("weighted_7d", 0.0))
    volume = min(weighted_7d / 7.0, 1.0)

    # Tendência: semana atual vs semana anterior
    weighted_14d = float(snapshot.get("weighted_14d", 0.0))
    prev_7d = max(0.0, weighted_14d - weighted_7d)
    trend_ratio = weighted_7d / max(0.1, prev_7d)
    trend = min(max(trend_ratio, 0.0), 2.0) / 2.0

    return round(0.4 * recency + 0.4 * volume + 0.2 * trend, 4)


def trend_arrow(trend_ratio: float | None) -> str:
    """Devolve indicador visual de tendência com base no rácio atual/anterior."""
    if trend_ratio is None:
        return "·"
    if trend_ratio >= 1.2:
        return "↗"
    if trend_ratio >= 0.8:
        return "→"
    return "↘"
