# CrownLedger

Clash Royale clan management tool. Analyses player activity, war performance, and helps scout recruitment candidates.

## Download

Get the latest Windows build from [Releases](https://github.com/zDud4s/crownledger-bot/releases). Extract the zip and run `CrownLedgerLocal.exe`.

## Setup

1. Get a Clash Royale API token at [developer.clashroyale.com](https://developer.clashroyale.com)
2. Open the app → Settings → paste the token → Save

## Features

- **Clan Health** — activity overview for all clan members
- **War Rank** — war performance ranking with fame and deck stats
- **Scout** — full player profile with activity score, mode utility, and war history
- **Updates** — detects and installs new versions automatically from Settings

---

## Development

### Run from source

```bash
pip install -r requirements-desktop.txt
python desktop/main.py
```

### Run tests

```bash
pytest tests/domain tests/app -q
```

### Release

Bump `desktop/version.py`, then:

```bash
git tag desktop-vX.Y.Z
git push origin desktop-vX.Y.Z
```

GitHub Actions builds and publishes the release automatically.
