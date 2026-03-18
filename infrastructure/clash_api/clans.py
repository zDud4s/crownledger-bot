from domain.infra.clash_api import ClashApiClient, encode_tag


def clan_members(clan_tag: str):
    client = ClashApiClient()
    tag = encode_tag(clan_tag)
    data = client.get(f"/clans/%23{tag}/members")
    return data["items"]
