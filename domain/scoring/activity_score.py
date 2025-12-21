import math
from bisect import bisect_left, bisect_right


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(x, hi))


def _pct_rank(x: float, sorted_vals: list[float]) -> float:
    """
    Percentil 0..1 com midrank.
    """
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0

    left = bisect_left(sorted_vals, x)
    right = bisect_right(sorted_vals, x)

    if right == 0:
        return 0.0
    if left >= n:
        return 1.0

    mid = (left + right - 1) / 2.0
    return clamp(mid / (n - 1))


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


def compute_activity_score(snapshot: dict, clan_baseline: dict | None = None) -> float:
    """
    Score em 0..1.
    - Se clan_baseline existir: score comparativo (percentis) e MULTIPLICATIVO.
    - Se não existir: fallback simples.
    """
    days_eff = float(snapshot["days_since_last_effective"])
    w7 = float(snapshot["weighted_7d"])
    w2 = float(snapshot["weighted_2d"])

    total = float(snapshot.get("battles_total_fetched", 0.0))
    days_with = float(snapshot.get("days_with_battles", 0.0))

    raw_7d = float(snapshot.get("raw_7d", 0.0))
    eff_7d = float(snapshot.get("effective_7d", 0.0))

    rec = (-days_eff) if math.isfinite(days_eff) else -1e9
    sat = min(total, 40.0)
    den = total / max(1.0, days_with)
    ratio = (eff_7d / raw_7d) if raw_7d > 0 else 0.0

    # Se não houve nenhuma batalha efetiva (e days_eff é inf), define score 0 direto
    if not math.isfinite(days_eff) and eff_7d == 0:
        return 0.0

    if clan_baseline is not None:
        p_rec = _pct_rank(rec, clan_baseline["rec"])      # mais recente -> maior
        p_w7 = _pct_rank(w7, clan_baseline["w7"])
        p_w2 = _pct_rank(w2, clan_baseline["w2"])
        p_sat = _pct_rank(sat, clan_baseline["sat"])
        p_den = _pct_rank(den, clan_baseline["den"])
        p_ratio = _pct_rank(ratio, clan_baseline["ratio"])

        # Índices 0..1 (agregações com interpretação)
        recency_i = p_rec
        volume_i = clamp(0.75 * p_w7 + 0.25 * p_w2)
        log_i = clamp(0.60 * p_sat + 0.40 * p_den)
        quality_i = p_ratio

        # Produto com expoentes (pesa recency e volume mais)
        # eps evita zero “matemático” quando há empates no percentil.
        eps = 1e-4
        recency_i = max(eps, recency_i)
        volume_i = max(eps, volume_i)
        log_i = max(eps, log_i)
        quality_i = max(eps, quality_i)

        score = (
            (recency_i ** 0.45) *
            (volume_i  ** 0.30) *
            (log_i     ** 0.20) *
            (quality_i ** 0.05)
        )
        return round(score, 3)

    # Fallback absoluto (sem baseline)
    if not math.isfinite(days_eff):
        recency_score = 0.0
    else:
        recency_score = clamp(1.0 - days_eff / 7.0)

    vol7 = clamp(w7 / 50.0)
    vol2 = clamp(w2 / 15.0)
    sat_s = clamp(sat / 40.0)
    den_s = clamp(math.log1p(den) / math.log1p(40.0))
    ratio_s = clamp(ratio)

    score = (
        0.40 * recency_score +
        0.25 * vol7 +
        0.10 * vol2 +
        0.15 * sat_s +
        0.05 * den_s +
        0.05 * ratio_s
    )
    return round(score, 3)
