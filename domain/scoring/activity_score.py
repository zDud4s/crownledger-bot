import math


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(x, hi))


def _span_factor(days_since_oldest: float, full_at_days: float = 2.0, zero_at_days: float = 15.0) -> float:
    if not math.isfinite(days_since_oldest):
        return 0.0
    if days_since_oldest <= full_at_days:
        return 1.0
    if days_since_oldest >= zero_at_days:
        return 0.0
    return 1.0 - ((days_since_oldest - full_at_days) / (zero_at_days - full_at_days))


def compute_clan_baseline(profiles: list) -> dict:
    """
    Sorted lists for percentiles (intra-clan comparison).
    Accepts list of ActivityProfile or list of dicts.
    """
    rec_vals = []
    w7_vals = []
    raw7_vals = []
    sat_vals = []
    den_vals = []

    for s in profiles:
        # Duck-typed: supports ActivityProfile and legacy dict
        def _get(key, default=0.0):
            if isinstance(s, dict):
                return float(s.get(key, default))
            return float(getattr(s, key, default))

        days_any = _get("days_since_last_any", float("inf"))
        w7 = _get("weighted_7d")
        raw7 = _get("raw_7d")
        total = _get("battles_total", _get("battles_total_fetched"))
        days_with = _get("days_with_battles")

        rec = (-days_any) if math.isfinite(days_any) else -1e9
        sat = min(total, 40.0)
        den = total / max(1.0, days_with)

        rec_vals.append(rec)
        w7_vals.append(w7)
        raw7_vals.append(raw7)
        sat_vals.append(sat)
        den_vals.append(den)

    return {
        "rec": sorted(rec_vals),
        "w7": sorted(w7_vals),
        "raw7": sorted(raw7_vals),
        "sat": sorted(sat_vals),
        "den": sorted(den_vals),
    }


def compute_activity_score(snapshot) -> float:
    """
    Score 0.0–1.0 based solely on volume and recency.
    Does NOT penalize by battle type (that is battle_utility's job).

    Accepts ActivityProfile (dataclass) or dict with compatible fields.
    """
    N_ACTIVE = 30

    # Duck-typed: supports ActivityProfile and legacy dict
    if isinstance(snapshot, dict):
        total = float(snapshot.get("battles_total", snapshot.get("battles_total_fetched", 0.0)))
        days_since_oldest = float(snapshot.get("days_since_oldest", float("inf")))
    else:
        total = float(snapshot.battles_total)
        days_since_oldest = float(snapshot.days_since_oldest)

    if total <= 0:
        return 0.0

    span = _span_factor(days_since_oldest, full_at_days=2.0, zero_at_days=15.0)

    if total < N_ACTIVE:
        # <30 => score below 0.5 (punitive for low volume)
        main = (total / N_ACTIVE) ** 2
        score = 0.5 * main
    else:
        # >=30 => score never below 0.5; bonus for recency
        score = 0.5 + 0.5 * span

    return round(clamp(score), 3)
