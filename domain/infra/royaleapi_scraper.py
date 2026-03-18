from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Garante que só um scrape corre de cada vez
_scrape_lock = asyncio.Semaphore(1)


@dataclass
class WarWeekRecord:
    season_week: str      # e.g. "130-2"
    date: str             # "YYYY-MM-DD"
    clan_rank: int
    league: str
    clan_name: str
    decks_used: int
    fame: int
    repair_points: int
    boat_attacks: int
    total: int


_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-PT', 'pt', 'en']});
window.chrome = {runtime: {}};
"""

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]

_BLOCKED_DOMAINS = [
    "privacy-mgmt.com",
    "pubmatic.com",
    "openx.net",
    "pub.network",
    "googlesyndication.com",
    "doubleclick.net",
    "rlcdn.com",
    "liveramp.com",
]

# Script injectado na página para extrair o token JWT e chamar a API directamente.
# Evita qualquer interacção com o DOM (cliques, overlays, etc.).
_FETCH_CW2_SCRIPT = """
async (tag) => {
    const scripts = [...document.querySelectorAll('script')].filter(s => !s.src);
    const text = scripts.map(s => s.textContent).join('');

    const tokenMatch = text.match(/token:\\s*'([^']+)'/);
    if (!tokenMatch) return { error: 'no_token' };

    const clanMatch = text.match(/clan_tag:\\s*'([^']+)'/);
    if (!clanMatch) return { error: 'no_clan' };

    const token = tokenMatch[1];
    const clanTag = clanMatch[1];

    const r = await fetch(`/player/cw2_history/${tag}?clan_tag=${clanTag}`, {
        headers: { 'Authorization': 'Bearer ' + token }
    });

    if (!r.ok) return { error: 'api_error', status: r.status };
    return await r.json();
}
"""


async def _block_ads(route):
    if any(d in route.request.url for d in _BLOCKED_DOMAINS):
        await route.abort()
    else:
        await route.continue_()


async def get_player_war_history(player_tag: str) -> list[WarWeekRecord] | None:
    """
    Fetch Clan Wars 2 history from royaleapi.com for the given player tag.
    Returns all available war weeks, ordered from most recent to oldest.
    Returns None on error (timeout/scraping failure), [] if no history found.
    """
    async with _scrape_lock:
        return await _scrape_war_history(player_tag)


async def _scrape_war_history(player_tag: str) -> list[WarWeekRecord] | None:
    tag = player_tag.strip().upper()
    if tag.startswith("#"):
        tag = tag[1:]

    url = f"https://royaleapi.com/player/{tag}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=_LAUNCH_ARGS)
            try:
                context = await browser.new_context(user_agent=_USER_AGENT)
                await context.add_init_script(_STEALTH_SCRIPT)

                page = await context.new_page()
                await page.route("**/*", _block_ads)

                response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

                if response is None or response.status == 404:
                    logger.warning("royaleapi: player %s not found (404)", tag)
                    return []

                # Aguardar que o jQuery e os handlers inline estejam prontos
                try:
                    await page.wait_for_function(
                        "() => typeof $ !== 'undefined' && $('.cw2_history_button').length > 0",
                        timeout=15_000,
                    )
                except PlaywrightTimeout:
                    logger.warning("royaleapi: page JS not ready for %s", tag)
                    return []

                # Extrair token JWT da página e chamar a API directamente
                result = await page.evaluate(_FETCH_CW2_SCRIPT, tag)

                if not isinstance(result, dict):
                    logger.warning("royaleapi: unexpected result type for %s: %s", tag, result)
                    return None

                if result.get("error"):
                    error = result["error"]
                    if error == "no_clan":
                        logger.info("royaleapi: player %s has no clan, no war history", tag)
                        return []
                    if error == "no_token":
                        logger.warning("royaleapi: no token found in page for %s", tag)
                        return None
                    logger.warning("royaleapi: API error %s for %s", result.get("status"), tag)
                    return None

                rows = result.get("rows") or []
                records: list[WarWeekRecord] = []
                for row in rows:
                    try:
                        records.append(WarWeekRecord(
                            season_week=f"{row['season_id']}-{row['section_index']}",
                            date=row.get("log_date", ""),
                            clan_rank=int(row.get("clan_rank_int", 0)),
                            league=row.get("clan_league", ""),
                            clan_name=row.get("clan_name", ""),
                            decks_used=int(row.get("decks_used", 0)),
                            fame=int(row.get("fame", 0)),
                            repair_points=int(row.get("repair_points", 0)),
                            boat_attacks=int(row.get("boat_attacks", 0)),
                            total=int(row.get("contribution", 0)),
                        ))
                    except (KeyError, ValueError, TypeError) as exc:
                        logger.debug("royaleapi: skipping malformed row %s: %s", row, exc)

                logger.info("royaleapi: fetched %d war weeks for %s", len(records), tag)
                return records

            finally:
                await browser.close()

    except PlaywrightTimeout:
        logger.warning("royaleapi: timeout loading page for %s", tag)
        return None
    except Exception as exc:
        logger.warning("royaleapi: unexpected error for %s: %s", tag, exc)
        return None
