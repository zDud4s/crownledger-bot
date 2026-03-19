from __future__ import annotations

import asyncio
import math
from typing import Optional

import discord
import requests
from discord import app_commands
from discord.ext import commands

from app.services.clan_service import fetch_players_with_battles
from app.use_cases.clan_health import ClanHealthReport, PlayerHealth, compute_clan_health
from domain.scoring.recent_activity_score import trend_arrow

_PAGE_SIZE = 10
_EMBED_COLOR = 0x2B2D31
_INDENT = "\u2003"


# ── helpers visuais ────────────────────────────────────────────────────────────

def _score_bar(score: float, length: int = 10) -> str:
    filled = round(score * length)
    return "▰" * filled + "▱" * (length - filled)


def _tier_emoji(tier: str) -> str:
    return {"inactive": "🔴", "at_risk": "🟡", "active": "🟢"}.get(tier, "⚪")


def _tier_label(tier: str) -> str:
    return {"inactive": "INATIVOS", "at_risk": "EM RISCO", "active": "ATIVOS"}.get(tier, tier)


_SECTION_SEP = "─" * 28


def _format_entry(ph: PlayerHealth, tier: str) -> list[str]:
    """Devolve 3 linhas por jogador no estilo /war-rank."""
    emoji = _tier_emoji(tier)

    # Dias desde última batalha (qualquer)
    d = ph.days_since_last_any
    days_str = f"`{'∞':>4}`" if not math.isfinite(float(d)) else f"`{float(d):>4.1f}d`"

    # Batalhas nos últimos 7 dias (contagem bruta)
    raw7 = f"`{ph.raw_7d:>2}`"

    # Tendência
    arrow = trend_arrow(ph.trend_ratio)

    bar = _score_bar(ph.score)
    score_str = f"`{ph.score:.2f}`"

    util_bar = _score_bar(ph.battle_utility)
    util_str = f"`{ph.battle_utility:.2f}`"

    line1 = f"**{ph.name}** — {emoji} ativ. {score_str}"
    line2 = f"{_INDENT}{bar}  📅 {days_str} sem jogar · ⚔️ {raw7}/7d · {arrow}"
    line3 = f"{_INDENT}{util_bar}  🎯 utilidade {util_str}"
    return [line1, line2, line3]


# ── construção das páginas ─────────────────────────────────────────────────────

def _build_health_pages(
    report: ClanHealthReport,
    show_active: bool,
) -> list[discord.Embed]:
    clan_tag = report.clan_tag

    # Lista ordenada: inativos → em risco → (ativos se show_active)
    entries: list[tuple[str, PlayerHealth]] = (
        [("inactive", p) for p in report.inactive]
        + [("at_risk", p) for p in report.at_risk]
        + ([("active", p) for p in report.active] if show_active else [])
    )

    # Resumo dos ativos para o footer de cada página
    na = len(report.active)
    avg_active = sum(p.score for p in report.active) / na if na else 0.0
    active_hint = (
        f"🟢 ATIVOS — {na} jogadores · score médio {avg_active:.2f}"
        + ("" if show_active else "  *(show_active:True para ver lista)*")
    )

    if not entries:
        # Nenhum inativo/em risco — embed único
        embed = discord.Embed(
            title=f"🏰 Clan Health — {clan_tag}",
            description=f"Nenhum jogador inativo ou em risco.\n\n{active_hint}",
            color=_EMBED_COLOR,
        )
        embed.timestamp = discord.utils.utcnow()
        return [embed]

    chunks = [entries[i : i + _PAGE_SIZE] for i in range(0, len(entries), _PAGE_SIZE)]
    total_pages = len(chunks)
    pages: list[discord.Embed] = []

    for page_idx, chunk in enumerate(chunks, start=1):
        lines: list[str] = []
        prev_tier: str | None = None

        for tier, ph in chunk:
            # Cabeçalho de secção quando o tier muda
            if tier != prev_tier:
                if lines:  # separador entre secções
                    lines.append(_SECTION_SEP)
                count = len(report.inactive) if tier == "inactive" else (
                    len(report.at_risk) if tier == "at_risk" else len(report.active)
                )
                label = "jogador" if count == 1 else "jogadores"
                lines.append(f"{_tier_emoji(tier)} **{_tier_label(tier)}** — {count} {label}")
                prev_tier = tier

            lines.extend(_format_entry(ph, tier))

        embed = discord.Embed(
            title=f"🏰 Clan Health — {clan_tag}  ·  {report.total_members} membros",
            description="\n".join(lines),
            color=_EMBED_COLOR,
        )
        embed.add_field(name="", value=active_hint, inline=False)
        embed.set_footer(
            text=f"Página {page_idx}/{total_pages} · Score: recência 40% · volume 40% · tendência 20%"
        )
        embed.timestamp = discord.utils.utcnow()
        pages.append(embed)

    return pages


# ── view de paginação ──────────────────────────────────────────────────────────

class ClanHealthView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=120)
        self.pages = pages
        self.current = 0
        self.message: Optional[discord.Message] = None
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current == len(self.pages) - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass


# ── cog ───────────────────────────────────────────────────────────────────────

class ClanHealthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="clan-health",
        description="Mostra os jogadores inativos e em risco do clã.",
    )
    @app_commands.describe(
        clan_tag="Tag do clã (ex: #ABC123)",
        show_active="Incluir lista de jogadores ativos (default: False)",
    )
    async def clan_health(
        self,
        interaction: discord.Interaction,
        clan_tag: str,
        show_active: bool = False,
    ):
        if not clan_tag or not clan_tag.strip():
            await interaction.response.send_message(
                "Uso: `/clan-health clan_tag:#CLANTAG`", ephemeral=True
            )
            return

        clan_tag = clan_tag.strip().upper()
        if not clan_tag.startswith("#"):
            clan_tag = "#" + clan_tag

        await interaction.response.defer(thinking=True)

        try:
            players = await asyncio.to_thread(fetch_players_with_battles, clan_tag)
        except Exception as e:
            await interaction.followup.send(f"Erro ao obter dados do clã: `{e}`")
            return

        if not players:
            await interaction.followup.send(
                f"Nenhum membro encontrado para `{clan_tag}`.", ephemeral=True
            )
            return

        report = compute_clan_health(clan_tag, players)
        pages = _build_health_pages(report, show_active)

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0])
        else:
            view = ClanHealthView(pages)
            msg = await interaction.followup.send(embed=pages[0], view=view)
            view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(ClanHealthCog(bot))
