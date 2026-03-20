APP_NAME = "CrownLedger Local"
RELEASE_TAG_PREFIX = "desktop-v"
__version__ = "0.1.1"


def release_tag_for(version: str | None = None) -> str:
    return f"{RELEASE_TAG_PREFIX}{version or __version__}"
