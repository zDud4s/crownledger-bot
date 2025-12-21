import os
import requests
from dotenv import load_dotenv

load_dotenv()


class ClashApiClient:
    BASE_URL = "https://api.clashroyale.com/v1"

    def __init__(self):
        token = os.getenv("CLASH_API_TOKEN")
        if not token:
            raise RuntimeError("CLASH_API_TOKEN not set")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })

    def get(self, path: str, params=None):
        url = f"{self.BASE_URL}{path}"
        r = self.session.get(url, params=params, timeout=15)

        if r.status_code == 200:
            return r.json()

        # erros mais comuns
        if r.status_code == 403:
            raise RuntimeError("403 Forbidden: token inválido ou IP não whitelisted no portal da Supercell")
        if r.status_code == 404:
            raise RuntimeError("404 Not Found: tag inválida ou endpoint errado")
        if r.status_code == 429:
            raise RuntimeError("429 Too Many Requests: rate limit. Implementar retry/backoff depois")

        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
