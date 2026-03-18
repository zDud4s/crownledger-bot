from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote

import requests


API_BASE = "https://api.clashroyale.com/v1"


def encode_tag(tag: str) -> str:
    t = tag.strip().upper()
    if not t.startswith("#"):
        t = "#" + t
    return quote(t, safe="")


@dataclass
class ApiResponse:
    json: Any
    headers: dict[str, str]
    status_code: int


class ClashApiClient:
    def __init__(self, token: str, timeout_s: int = 20):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.timeout_s = timeout_s

    def _get(self, url: str, max_retries: int = 6) -> ApiResponse:
        """
        Backoff simples:
          - se 429: usa Retry-After ou x-ratelimit-reset (quando existir)
          - se 5xx: retry com backoff
        A API expõe limites via headers e devolve 429 quando atinges rate limit. :contentReference[oaicite:1]{index=1}
        """
        sleep_s = 1.0
        for attempt in range(1, max_retries + 1):
            r = self.session.get(url, timeout=self.timeout_s)

            if 200 <= r.status_code < 300:
                return ApiResponse(r.json(), dict(r.headers), r.status_code)

            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    wait = float(retry_after)
                else:
                    reset = r.headers.get("x-ratelimit-reset")
                    wait = float(reset) if reset else 10.0
                time.sleep(max(wait, 1.0))
                continue

            if 500 <= r.status_code < 600:
                time.sleep(sleep_s)
                sleep_s = min(sleep_s * 2.0, 30.0)
                continue

            r.raise_for_status()

        raise RuntimeError(f"GET falhou após {max_retries} tentativas: {url}")

    def get_clan_members(self, clan_tag: str) -> list[dict[str, Any]]:
        url = f"{API_BASE}/clans/{encode_tag(clan_tag)}/members"
        resp = self._get(url)
        items = resp.json.get("items", [])
        return items if isinstance(items, list) else []

    def get_player_battlelog(self, player_tag: str) -> list[dict[str, Any]]:
        url = f"{API_BASE}/players/{encode_tag(player_tag)}/battlelog"
        resp = self._get(url)
        return resp.json if isinstance(resp.json, list) else []

    def get_river_race_log(self, clan_tag: str, limit: int = 10) -> list[dict[str, Any]]:
        url = f"{API_BASE}/clans/{encode_tag(clan_tag)}/riverracelog?limit={limit}"
        resp = self._get(url)
        items = resp.json.get("items", [])
        return items if isinstance(items, list) else []

    def get_player_profile(self, player_tag: str) -> dict[str, Any]:
        url = f"{API_BASE}/players/{encode_tag(player_tag)}"
        resp = self._get(url)
        return resp.json if isinstance(resp.json, dict) else {}
