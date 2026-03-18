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

def compute_clan_baseline(snapshots: list[dict]) -> dict:
    """
    Listas ordenadas para percentis (comparação intra-clã).
    """
    rec_vals = []
    w7_vals = []
    w2_vals = []
    sat_vals = []
    den_vals = []
    ratio_vals = []

    for s in snapshots:
        days_eff = float(s["days_since_last_effective"])
        w7 = float(s["weighted_7d"])
        w2 = float(s["weighted_2d"])

        total = float(s.get("battles_total_fetched", 0.0))
        days_with = float(s.get("days_with_battles", 0.0))

        raw_7d = float(s.get("raw_7d", 0.0))
        eff_7d = float(s.get("effective_7d", 0.0))

        # Recency efetiva: -days; se inf, é muito mau
        rec = (-days_eff) if math.isfinite(days_eff) else -1e9

        # Saturação do log (cap 40)
        sat = min(total, 40.0)

        # Densidade (battles por dia em que jogou)
        den = total / max(1.0, days_with)

        # Qualidade: percentagem de batalhas "efetivas" nos últimos 7 dias
        ratio = (eff_7d / raw_7d) if raw_7d > 0 else 0.0

        rec_vals.append(rec)
        w7_vals.append(w7)
        w2_vals.append(w2)
        sat_vals.append(sat)
        den_vals.append(den)
        ratio_vals.append(ratio)

    return {
        "rec": sorted(rec_vals),
        "w7": sorted(w7_vals),
        "w2": sorted(w2_vals),
        "sat": sorted(sat_vals),
        "den": sorted(den_vals),
        "ratio": sorted(ratio_vals),
    }


def compute_activity_score(snapshot: dict) -> float:
    N_ACTIVE = 30
    X_EFF = 0.20  # x% de "efetividade" (bónus leve)

    total = float(snapshot.get("battles_total_fetched", 0.0))
    days_since_oldest = float(snapshot.get("days_since_oldest", float("inf")))
    eff_ratio = float(snapshot.get("effective_ratio_total", 0.0))

    if total <= 0:
        return 0.0

    span = _span_factor(days_since_oldest, full_at_days=2.0, zero_at_days=15.0)

    # componente de efetividade que NÃO penaliza bursts casuais
    # se eff_ratio=0 => eff_part = span (2 dias => 1, 15 dias => 0)
    eff_part = clamp(eff_ratio + (1.0 - eff_ratio) * span)

    if total < N_ACTIVE:
        # <30 => score abaixo de 0.5 (bem punitivo)
        main = (total / N_ACTIVE) ** 2  # 0..1
        score = 0.5 * main
    else:
        # >=30 => score NUNCA abaixo de 0.5
        top = (1.0 - X_EFF) * span + X_EFF * eff_part  # 0..1
        score = 0.5 + 0.5 * top

    return round(clamp(score), 3)
