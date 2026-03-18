from __future__ import annotations

import asyncio
from typing import Optional

import discord
import requests
from discord import app_commands
from discord.ext import commands

from app.use_cases.war_rank import WarPlayerStats, rank_players_by_war_utility

_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
_PAGE_SIZE = 10
_EMBED_COLOR = 0xF5C518  # dourado
_PODIUM_SEP = "─" * 28
_INDENT = "\u2003"      # em space — indentação visual da linha de stats


def _score_bar(score: float, length: int = 10) -> str:
    filled = round(score * length)
    return "▰" * filled + "▱" * (length - filled)


def _score_tier(score: float) -> str:
    if score >= 0.75:
        return "🔥"
    if score >= 0.50:
        return "✅"
    return "⚠️"


def _format_entry(rank: int, p: WarPlayerStats, actual_n: int) -> list[str]:
    """Devolve 2 linhas por jogador: [nome+score, barra+stats]."""
    medal = _MEDALS.get(rank)
    prefix = medal if medal else f"`{rank}`"
    name = p.name or "?"
    tier = _score_tier(p.war_utility)
    score = f"`{p.war_utility:.2f}`"

    bar = _score_bar(p.war_utility)
    wars = f"{p.wars_participated}/{actual_n}"
    part = f"`{int(p.participation * 100):>3}%`"
    fame = f"`{int(p.mean_fame_per_deck):>3}`"

    line1 = f"{prefix} **{name}** — {tier} util. {score}"
    line2 = f"{_INDENT}{bar}  ⚔️ {wars} guerras · 🃏 {part} part. · ⭐ {fame} fame/deck"
    return [line1, line2]


def _build_war_rank_pages(
    clan_tag: str,
    players: list[WarPlayerStats],
    actual_n: int,
) -> list[discord.Embed]:
    total = len(players)
    chunks = [players[i : i + _PAGE_SIZE] for i in range(0, total, _PAGE_SIZE)]
    total_pages = len(chunks)
    pages: list[discord.Embed] = []

    for page_idx, chunk in enumerate(chunks, start=1):
        start_rank = (page_idx - 1) * _PAGE_SIZE + 1
        lines: list[str] = []
        for i, p in enumerate(chunk):
            rank = start_rank + i
            entry = _format_entry(rank, p, actual_n)
            lines.extend(entry)
            # separador visual após pódio (apenas na página 1, após rank 3)
            if page_idx == 1 and rank == 3 and len(chunk) > 3:
                lines.append(_PODIUM_SEP)

        embed = discord.Embed(
            title=f"🏆 Ranking de Utilidade em Guerras — {clan_tag}",
            description="\n".join(lines),
            color=_EMBED_COLOR,
        )
        embed.set_footer(
            text=f"Página {page_idx}/{total_pages} · {total} jogadores · Últimas {actual_n} guerras"
        )
        embed.timestamp = discord.utils.utcnow()
        pages.append(embed)

    return pages


class WarRankView(discord.ui.View):
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


class WarRankCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="war-rank",
        description="Ranking de utilidade dos membros do clã nas guerras (River Race).",
    )
    @app_commands.describe(
        clan_tag="Tag do clã (ex: #ABC123)",
        wars="Número de guerras a analisar (1-10, padrão 5)",
    )
    async def war_rank(
        self,
        interaction: discord.Interaction,
        clan_tag: str,
        wars: int = 5,
    ):
        if not clan_tag or not clan_tag.strip():
            await interaction.response.send_message(
                "Uso: `/war-rank clan_tag:#CLANTAG wars:5`", ephemeral=True
            )
            return

        wars = max(1, min(int(wars), 10))

        clan_tag = clan_tag.strip().upper()
        if not clan_tag.startswith("#"):
            clan_tag = "#" + clan_tag

        await interaction.response.defer(thinking=True)

        try:
            players = await asyncio.to_thread(rank_players_by_war_utility, clan_tag, wars)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                await interaction.followup.send("Clã não encontrado.", ephemeral=True)
            else:
                await interaction.followup.send(f"Erro ao obter dados: `{e}`")
            return
        except Exception as e:
            await interaction.followup.send(f"Erro ao obter dados: `{e}`")
            return

        if not players:
            await interaction.followup.send(
                "Nenhum dado de guerra encontrado para este clã.", ephemeral=True
            )
            return

        actual_n = players[0].total_wars
        pages = _build_war_rank_pages(clan_tag, players, actual_n)

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0])
        else:
            view = WarRankView(pages)
            msg = await interaction.followup.send(embed=pages[0], view=view)
            view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(WarRankCog(bot))
