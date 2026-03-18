from domain.infra.clash_api import ClashApiClient
from domain.infra.clash_api import encode_tag


def player_battlelog(player_tag: str):
    client = ClashApiClient()
    tag = encode_tag(player_tag)
    data = client.get(f"/players/%23{tag}/battlelog")
    return data
