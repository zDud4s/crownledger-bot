from infrastructure.clash_api.client import ClashApiClient
from infrastructure.clash_api.clans import sanitize_tag


def player_battlelog(player_tag: str):
    client = ClashApiClient()
    tag = sanitize_tag(player_tag)
    data = client.get(f"/players/%23{tag}/battlelog")
    return data
