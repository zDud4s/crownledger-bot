from infrastructure.clash_api.client import ClashApiClient


def sanitize_tag(tag: str) -> str:
    tag = tag.strip().upper()
    if tag.startswith("#"):
        tag = tag[1:]
    return tag


def clan_members(clan_tag: str):
    client = ClashApiClient()
    tag = sanitize_tag(clan_tag)
    data = client.get(f"/clans/%23{tag}/members")
    return data["items"]
