# scripts/train_inactivity_model.py
from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from domain.ml.dataset import build_inactivity_dataset, DatasetConfig
from domain.ml.model import train_inactivity_model, save_model


API_BASE = "https://api.clashroyale.com/v1"
load_dotenv()


@dataclass
class Battle:
    timestamp: datetime
    raw_json: dict[str, Any]


@dataclass
class Player:
    tag: str
    name: str
    battles: list[Battle]


def _encode_tag(tag: str) -> str:
    t = tag.strip()
    if not t.startswith("#"):
        t = "#" + t
    return quote(t, safe="")


def _parse_battle_time(s: str) -> datetime:
    """
    Formato típico: '20200102T030405.000Z'
    """
    x = s.strip()
    if x.endswith("Z"):
        x = x[:-1]

    if "." in x:
        base, frac = x.split(".", 1)
    else:
        base, frac = x, "0"

    dt = datetime.strptime(base, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)

    # frac pode ter 3 casas (ms) ou mais; convertemos para microsegundos
    frac_digits = "".join(ch for ch in frac if ch.isdigit())
    if frac_digits:
        frac_digits = (frac_digits + "000000")[:6]
        dt = dt.replace(microsecond=int(frac_digits))
    return dt


class ClashRoyaleClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_clan_members(self, clan_tag: str) -> list[dict[str, Any]]:
        url = f"{API_BASE}/clans/{_encode_tag(clan_tag)}/members"
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("items", [])

    def get_player_battlelog(self, player_tag: str) -> list[dict[str, Any]]:
        url = f"{API_BASE}/players/{_encode_tag(player_tag)}/battlelog"
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        return r.json()


def load_players_from_api(clan_tag: str, max_members: int = 50, sleep_s: float = 0.15) -> list[Player]:
    token = os.getenv("CLASH_API_TOKEN")
    if not token:
        raise RuntimeError("Falta a env var CLASH_API_TOKEN.")

    client = ClashRoyaleClient(token)

    members = client.get_clan_members(clan_tag)[:max_members]

    players: list[Player] = []
    for i, m in enumerate(members, start=1):
        ptag = m.get("tag")
        pname = m.get("name", ptag)

        if not ptag:
            continue

        try:
            battlelog = client.get_player_battlelog(ptag)
        except Exception as e:
            print(f"[{i}/{len(members)}] erro battlelog {ptag}: {e}")
            continue

        battles: list[Battle] = []
        for b in battlelog:
            bt = b.get("battleTime")
            if not bt:
                continue
            try:
                ts = _parse_battle_time(bt)
            except Exception:
                continue
            battles.append(Battle(timestamp=ts, raw_json=b))

        players.append(Player(tag=ptag, name=pname, battles=battles))

        # evita levar rate-limit
        time.sleep(sleep_s)

    return players


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clan-tag", required=True, help="Ex: #ABCD1234 (podes passar sem # também)")
    ap.add_argument("--model-out", default="models/inactivity_7d.joblib")
    ap.add_argument("--horizon-days", type=int, default=7)
    ap.add_argument("--snapshot-step-days", type=int, default=1)
    ap.add_argument("--min-history-days", type=int, default=3)
    ap.add_argument("--max-members", type=int, default=50)
    args = ap.parse_args()

    players = load_players_from_api(args.clan_tag, max_members=args.max_members)

    cfg = DatasetConfig(
        horizon_days=args.horizon_days,
        snapshot_step_days=args.snapshot_step_days,
        min_history_days=args.min_history_days,
    )

    df = build_inactivity_dataset(players, cfg)
    print(f"dataset rows: {len(df)}")
    if df.empty:
        print("Dataset vazio. Com battlelog curto pode não haver histórico suficiente.")
        return

    res = train_inactivity_model(df)
    print(f"trained samples={res.n_samples} positive_rate={res.positive_rate:.3f} roc_auc={res.roc_auc:.3f}")

    save_model(res.model, args.model_out)
    print(f"saved model -> {Path(args.model_out).resolve()}")


if __name__ == "__main__":
    main()
