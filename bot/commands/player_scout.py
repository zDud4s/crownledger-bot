from __future__ import annotations

import requests

import discord
from discord import app_commands
from discord.ext import commands

from app.use_cases.player_scout import PlayerScoutReport, scout_player


# ── helpers visuais ────────────────────────────────────────────────────────────

_EMBED_COLOR = 0x5865F2   # roxo azulado (blurple Discord)


def _score_bar(score: float, length: int = 12) -> str:
    filled = round(max(0.0, min(1.0, score)) * length)
    return "▰" * filled + "▱" * (length - filled)


def _score_tier(score: float) -> str:
    if score >= 0.75:
        return "🔥"
    if score >= 0.50:
        return "✅"
    return "⚠️"


def _candidate_label(score: float) -> str:
    if score >= 0.75:
        return "🔥  EXCELENTE CANDIDATO"
    if score >= 0.55:
        return "✅  BOA ESCOLHA"
    if score >= 0.35:
        return "⚠️  CONSIDERAR"
    return "❌  NÃO RECOMENDADO"


def _trend_arrow(ratio: float | None) -> str:
    if ratio is None:
        return "—"
    if ratio >= 1.2:
        return "↗ a subir"
    if ratio < 0.8:
        return "↘ a descer"
    return "→ estável"


def _days_label(days: float) -> str:
    if days == float("inf"):
        return "nunca"
    d = int(days)
    if d == 0:
        return "hoje"
    if d == 1:
        return "1 dia"
    return f"{d} dias"


# ── embed builder ──────────────────────────────────────────────────────────────

def _build_embed(r: PlayerScoutReport, war_weeks: int) -> discord.Embed:
    total_games = r.wins + r.losses
    win_rate = int(r.wins / max(total_games, 1) * 100)
    clan_str = f"🏰 {r.current_clan_name}" if r.current_clan_name else "🚫 Sem clã"

    embed = discord.Embed(
        title=f"🔍  {r.name}  ·  {r.tag}",
        description=clan_str,
        color=_EMBED_COLOR,
    )

    # ── Perfil: 3 campos inline ──
    embed.add_field(
        name="🏆  Troféus",
        value=f"**{r.trophies:,}**\nMelhor: {r.best_trophies:,}",
        inline=True,
    )
    embed.add_field(
        name="⚔️  Combate",
        value=f"**{r.wins:,}V** · {r.losses:,}D\nTaxa: {win_rate}%",
        inline=True,
    )
    embed.add_field(
        name="🎖️  Nível",
        value=f"**{r.level}**",
        inline=True,
    )

    # ── Atividade ──
    act_bar = _score_bar(r.activity_score)
    act_tier = _score_tier(r.activity_score)
    util_bar = _score_bar(r.battle_utility)
    util_tier = _score_tier(r.battle_utility)
    days_any_str = _days_label(r.days_since_last_any)
    days_eff_str = _days_label(r.days_since_last_effective)
    trend_str = _trend_arrow(r.trend_ratio)

    embed.add_field(
        name="🎮  Atividade Recente",
        value=(
            f"{act_bar} act. `{r.activity_score:.2f}` {act_tier}\n"
            f"  📅 Última batalha {'**hoje**' if days_any_str == 'hoje' else f'há **{days_any_str}**'}"
            f"  ·  Última ranked {'**hoje**' if days_eff_str == 'hoje' else f'há **{days_eff_str}**'}\n"
            f"  ⚔️ Batalhas (7d): **{r.raw_7d}**  ·  Tendência: {trend_str}"
        ),
        inline=False,
    )

    embed.add_field(
        name="🎯  Utilidade de Modos",
        value=f"{util_bar} util. `{r.battle_utility:.2f}` {util_tier}",
        inline=False,
    )

    # ── Guerras ──
    if r.war_data_available:
        war_bar = _score_bar(r.war_utility)
        war_tier = _score_tier(r.war_utility)
        deck_pct = int(r.participation * 100)
        consistency_pct = int(r.consistency * 100)
        embed.add_field(
            name=f"⚔️  Guerras (últimas {r.wars_analyzed} semanas)",
            value=(
                f"{war_bar} util. `{r.war_utility:.2f}` {war_tier}\n"
                f"  🏅 Participação: **{r.wars_participated}/{r.wars_analyzed}** guerras  ·  Decks: **{deck_pct}%**\n"
                f"  ⭐ Fama média: **{int(r.mean_fame_per_deck)}**/deck  ·  Consistência: **{consistency_pct}%**"
            ),
            inline=False,
        )
    elif r.war_fetch_error:
        embed.add_field(
            name="⚔️  Guerras",
            value="❌  Erro ao obter dados de guerras (timeout/falha no scraping)",
            inline=False,
        )
    else:
        embed.add_field(
            name="⚔️  Guerras",
            value="⚠️  Sem histórico de guerras registado",
            inline=False,
        )

    # ── Candidato ──
    cand_bar = _score_bar(r.candidate_score)
    cand_label = _candidate_label(r.candidate_score)
    embed.add_field(
        name="🎯  Avaliação de Candidato",
        value=(
            f"{cand_bar} `{r.candidate_score:.2f}`\n"
            f"**{cand_label}**"
        ),
        inline=False,
    )

    embed.set_footer(text=f"Análise de {war_weeks} semanas de guerras  ·  royaleapi.com")
    embed.timestamp = discord.utils.utcnow()
    return embed


# ── cog ───────────────────────────────────────────────────────────────────────

class PlayerScoutCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="scout",
        description="Analisa um jogador como candidato ao clã (perfil, atividade e guerras).",
    )
    @app_commands.describe(
        player_tag="Tag do jogador (ex: #ABC123)",
        wars="Semanas de guerra a analisar (5-20, padrão 10)",
    )
    async def scout(
        self,
        interaction: discord.Interaction,
        player_tag: str,
        wars: int = 10,
    ):
        if not player_tag or not player_tag.strip():
            await interaction.response.send_message(
                "Uso: `/scout player_tag:#PLAYERTAG`", ephemeral=True
            )
            return

        wars = max(5, min(int(wars), 20))

        player_tag = player_tag.strip().upper()
        if not player_tag.startswith("#"):
            player_tag = "#" + player_tag

        await interaction.response.defer(thinking=True)

        try:
            report = await scout_player(player_tag, war_weeks=wars)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                await interaction.followup.send("Jogador não encontrado.", ephemeral=True)
            else:
                await interaction.followup.send(f"Erro ao obter dados: `{e}`", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Erro ao obter dados: `{e}`", ephemeral=True)
            return

        embed = _build_embed(report, wars)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PlayerScoutCog(bot))
