from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from domain.ml.features import compute_activity_features, to_dict
from domain.ml.model import load_model, predict_risk


API_BASE = "https://api.clashroyale.com/v1"
load_dotenv()

@dataclass
class Battle:
    timestamp: datetime
    raw_json: dict[str, Any]


def _encode_tag(tag: str) -> str:
    t = tag.strip()
    if not t.startswith("#"):
        t = "#" + t
    return quote(t, safe="")


def _parse_battle_time(s: str) -> datetime:
    x = s.strip()
    if x.endswith("Z"):
        x = x[:-1]
    if "." in x:
        base, frac = x.split(".", 1)
    else:
        base, frac = x, "0"
    dt = datetime.strptime(base, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    frac_digits = "".join(ch for ch in frac if ch.isdigit())
    if frac_digits:
        frac_digits = (frac_digits + "000000")[:6]
        dt = dt.replace(microsecond=int(frac_digits))
    return dt


def fetch_battlelog(player_tag: str) -> list[Battle]:
    token = os.getenv("CLASH_API_TOKEN")
    if not token:
        raise RuntimeError("Falta a env var CLASH_API_TOKEN.")

    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})

    url = f"{API_BASE}/players/{_encode_tag(player_tag)}/battlelog"
    r = s.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    battles: list[Battle] = []
    for b in data:
        bt = b.get("battleTime")
        if not bt:
            continue
        try:
            ts = _parse_battle_time(bt)
        except Exception:
            continue
        battles.append(Battle(timestamp=ts, raw_json=b))
    return battles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/inactivity_7d.joblib")
    ap.add_argument("--player-tag", required=True)
    args = ap.parse_args()

    model = load_model(args.model)
    battles = fetch_battlelog(args.player_tag)

    feats = compute_activity_features(battles, ref_time=datetime.now(timezone.utc))
    risk = predict_risk(model, to_dict(feats))

    print(f"player={args.player_tag} inactivity_risk_7d={risk:.3f} ({risk*100:.1f}%)")


if __name__ == "__main__":
    main()
