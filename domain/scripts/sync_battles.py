from __future__ import annotations

import argparse
import os
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from domain.storage.battle_store import BattleStore


API_BASE = "https://api.clashroyale.com/v1"
load_dotenv()


def _encode_tag(tag: str) -> str:
    t = tag.strip()
    if not t.startswith("#"):
        t = "#" + t
    return quote(t, safe="")


class ClashRoyaleClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_clan_members(self, clan_tag: str) -> list[dict]:
        url = f"{API_BASE}/clans/{_encode_tag(clan_tag)}/members"
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        return r.json().get("items", [])

    def get_player_battlelog(self, player_tag: str) -> list[dict]:
        url = f"{API_BASE}/players/{_encode_tag(player_tag)}/battlelog"
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clan-tag", required=True)
    ap.add_argument("--max-members", type=int, default=50)
    ap.add_argument("--sleep-s", type=float, default=0.15)
    args = ap.parse_args()

    token = os.getenv("CLASH_API_TOKEN")
    if not token:
        raise RuntimeError("Falta a env var CLASH_API_TOKEN.")

    client = ClashRoyaleClient(token)
    store = BattleStore()

    members = client.get_clan_members(args.clan_tag)[: args.max_members]
    print(f"members: {len(members)}")

    total_added = 0
    for i, m in enumerate(members, start=1):
        ptag = m.get("tag")
        pname = m.get("name", ptag)
        if not ptag:
            continue

        try:
            battlelog = client.get_player_battlelog(ptag)
            added = store.upsert_player_battles(ptag, battlelog)
            total_added += added
            print(f"[{i}/{len(members)}] {pname} {ptag}: +{added}")
        except Exception as e:
            print(f"[{i}/{len(members)}] erro {pname} {ptag}: {e}")

        time.sleep(args.sleep_s)

    print(f"done. total added: {total_added}")


if __name__ == "__main__":
    main()
