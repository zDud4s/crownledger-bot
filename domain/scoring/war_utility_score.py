from __future__ import annotations

_FAME_PER_DECK_NORM = 250.0  # normalization divisor; accounts for Colosseum-day multipliers
_MAX_DECKS_PER_WAR = 16      # 4 training days × 4 decks/day (battle day não conta no decksUsed)


def compute_war_utility(war_records: list[dict], total_wars: int) -> dict:
    """
    Compute war utility metrics for a single player.

    Args:
        war_records: list of {fame: int, decks_used: int} — one entry per war where
                     the player participated (decks_used > 0).
        total_wars:  actual number of races in the analysis window (N),
                     which may be less than the requested number if history is short.

    Returns dict with:
        participation    — deck usage rate within participated wars (0.0-1.0)
        fame_efficiency  — proxy for win rate, mean fame/deck normalised to 1.0 (0.0-1.0)
        consistency      — fraction of wars where player participated (0.0-1.0)
        war_utility      — composite score: 0.4*part + 0.4*fame_eff + 0.2*consistency
        mean_fame_per_deck — absolute mean fame per deck used (for display)
    """
    wars_participated = len(war_records)

    if wars_participated == 0 or total_wars == 0:
        return {
            "participation": 0.0,
            "fame_efficiency": 0.0,
            "consistency": 0.0,
            "war_utility": 0.0,
            "mean_fame_per_deck": 0.0,
        }

    total_decks = sum(r["decks_used"] for r in war_records)
    total_fame = sum(r["fame"] for r in war_records)

    participation = total_decks / (wars_participated * _MAX_DECKS_PER_WAR)
    participation = min(participation, 1.0)

    mean_fame_per_deck = total_fame / max(total_decks, 1)
    fame_efficiency = min(mean_fame_per_deck / _FAME_PER_DECK_NORM, 1.0)

    consistency = wars_participated / total_wars

    war_utility = round(0.4 * participation + 0.4 * fame_efficiency + 0.2 * consistency, 2)

    return {
        "participation": round(participation, 4),
        "fame_efficiency": round(fame_efficiency, 4),
        "consistency": round(consistency, 4),
        "war_utility": war_utility,
        "mean_fame_per_deck": round(mean_fame_per_deck, 1),
    }
