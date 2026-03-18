from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from domain.infra.clash_api import ClashApiClient
from domain.storage.sqlite_store import SqliteStore

load_dotenv()

def read_clans_file(path: Path) -> list[str]:
    clans: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("//"):
            continue
        if not t.startswith("#"):
            t = "#" + t
        clans.append(t.upper())
    return clans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/crownledger.sqlite")
    ap.add_argument("--clans-file", default="data/clans.txt")
    ap.add_argument("--max-members", type=int, default=50)
    ap.add_argument("--sleep-s", type=float, default=0.15)
    args = ap.parse_args()

    token = os.getenv("CLASH_API_TOKEN")
    if not token:
        raise RuntimeError("Falta CLASH_API_TOKEN no ambiente.")

    store = SqliteStore(args.db)
    client = ClashApiClient(token)

    clans_path = Path(args.clans_file)
    if not clans_path.exists():
        raise RuntimeError(f"Não existe clans-file: {clans_path}")

    clans = read_clans_file(clans_path)
    if not clans:
        raise RuntimeError("clans.txt está vazio.")

    total_added = 0
    total_players = 0

    for clan_tag in clans:
        store.upsert_clan(clan_tag)
        members = client.get_clan_members(clan_tag)[: args.max_members]
        print(f"clan {clan_tag}: members={len(members)}")

        for m in members:
            ptag = m.get("tag")
            if not ptag:
                continue
            ptag = ptag.upper()

            store.upsert_player(ptag)
            store.upsert_membership(clan_tag, ptag)
            total_players += 1

            battlelog = client.get_player_battlelog(ptag)
            added = store.insert_battles_delta(ptag, battlelog)
            total_added += added

            print(f"  {ptag}: +{added}")
            time.sleep(args.sleep_s)

    store.close()
    print(f"done. players_seen={total_players} battles_added={total_added}")


if __name__ == "__main__":
    main()
