import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from app.services.clan_service import fetch_players_with_battles
from app.use_cases.rank_clan import rank_players


def _safe_str(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _fmt_days(x) -> str:
    if x == float("inf"):
        return "inf"
    try:
        return f"{float(x):.1f}d"
    except Exception:
        return "n/a"


def _fmt_float(x) -> str:
    try:
        return f"{float(x):.2f}"
    except Exception:
        return "n/a"


def _build_rank_embed(clan_tag: str, ranking, limit: int) -> discord.Embed:
    shown = min(limit, len(ranking))

    embed = discord.Embed(
        title=f"Activity ranking — {clan_tag}",
        description="",
    )
    embed.timestamp = discord.utils.utcnow()

    header = f"{'#':>2}  {'Nome':<18}  {'Score':>6}  {'LastAny':>7}  {'Eff7d':>5}  {'W7d':>6}"
    lines = [header, "-" * len(header)]

    for i, p in enumerate(ranking[:shown], start=1):
        snap = p.activity_snapshot()

        name = _safe_str(getattr(p, "name", "Unknown"), 18)
        score = _fmt_float(p.activity_score())
        last_any = _fmt_days(snap.get("days_since_last_any"))
        eff7 = str(snap.get("effective_7d", "n/a"))
        w7 = _fmt_float(snap.get("weighted_7d"))

        lines.append(f"{i:>2}  {name:<18}  {score:>6}  {last_any:>7}  {eff7:>5}  {w7:>6}")

    table = "\n".join(lines)

    # Discord embed description limit: 4096 chars
    if len(table) > 3900:
        table = table[:3900] + "\n..."

    embed.description = f"```text\n{table}\n```"
    embed.set_footer(text=f"Mostrando top {shown}/{len(ranking)} | Atualizado agora")
    return embed


class RankCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="rank",
        description="Mostra o ranking de atividade do clã (do mais ativo para o menos ativo).",
    )
    @app_commands.describe(
        clan_tag="Tag do clã (ex: #ABC123)",
        limit="Quantos membros mostrar (máx 50)",
    )
    async def rank(self, interaction: discord.Interaction, clan_tag: str, limit: int = 50):
        if not clan_tag or not clan_tag.strip():
            await interaction.response.send_message("Uso: `/rank clan_tag:#CLANTAG limit:20`", ephemeral=True)
            return

        limit = max(1, min(int(limit), 50))

        clan_tag = clan_tag.strip().upper()
        if not clan_tag.startswith("#"):
            clan_tag = "#" + clan_tag

        await interaction.response.defer(thinking=True)

        try:
            players = await asyncio.to_thread(fetch_players_with_battles, clan_tag)
            ranking = rank_players(players)
        except Exception as e:
            await interaction.followup.send(f"Erro ao obter dados: `{e}`")
            return

        embed = _build_rank_embed(clan_tag, ranking, limit)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RankCog(bot))
