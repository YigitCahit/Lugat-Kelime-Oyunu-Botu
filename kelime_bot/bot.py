from __future__ import annotations

import asyncio
import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from .database import Database, LeaderboardType
from .text_utils import normalize_word
from .word_bank import WordBank

LOGGER = logging.getLogger(__name__)


class WordGameCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database, word_bank: WordBank) -> None:
        self.bot = bot
        self.db = db
        self.word_bank = word_bank
        self.guild_locks: dict[int, asyncio.Lock] = {}

    def _guild_lock(self, guild_id: int) -> asyncio.Lock:
        lock = self.guild_locks.get(guild_id)
        if lock is None:
            lock = asyncio.Lock()
            self.guild_locks[guild_id] = lock
        return lock

    async def _ensure_guild_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is not None:
            return True

        if interaction.response.is_done():
            await interaction.followup.send(
                "Bu komut yalnızca sunucularda kullanılabilir.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Bu komut yalnızca sunucularda kullanılabilir.",
                ephemeral=True,
            )
        return False

    async def _ensure_manage_guild(self, interaction: discord.Interaction) -> bool:
        if not await self._ensure_guild_interaction(interaction):
            return False

        if not isinstance(interaction.user, discord.Member):
            return False

        if interaction.user.guild_permissions.manage_guild:
            return True

        message = "Bu komut için 'Sunucuyu Yönet' izni gerekiyor."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return False

    async def _handle_invalid_word(
        self,
        message: discord.Message,
        settings: dict[str, Any],
        reason: str,
    ) -> None:
        if settings["delete_wrong_words"]:
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

        if settings["send_warning"]:
            try:
                warning_message = await message.channel.send(
                    f"{message.author.mention} {reason}"
                )
                await warning_message.delete(delay=6)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @staticmethod
    def _format_settings(settings: dict[str, Any]) -> str:
        channel_display = (
            f"<#{settings['game_channel_id']}>"
            if settings["game_channel_id"]
            else "Ayarlanmadı"
        )

        return (
            f"Kanal: {channel_display}\n"
            f"Yanlış kelime silme: {'Açık' if settings['delete_wrong_words'] else 'Kapalı'}\n"
            f"Uyarı mesajı: {'Açık' if settings['send_warning'] else 'Kapalı'}\n"
            f"Doğru kelime reaksiyonu: {'Açık' if settings['react_correct_words'] else 'Kapalı'}\n"
            f"Kaçış karakteri: {settings['escape_prefix']}\n"
            f"Reaksiyon emojisi: {settings['reaction_emoji']}\n"
            f"Kelime puanı: {settings['points_per_word']}\n"
            f"Seviye atlama puanı: {settings['level_up_points']}\n"
            f"Sıfırlama kelime sayısı: {settings['reset_after_words']}\n"
            f"Aynı kişi arka arkaya oynayabilir: {'Evet' if settings['allow_consecutive_turns'] else 'Hayır'}"
        )

    async def _publish_round_results_and_reset(
        self,
        guild: discord.Guild,
        target_channel: discord.TextChannel,
        round_id: int,
        trigger_text: str,
    ) -> None:
        rows = await self.db.get_round_leaderboard(guild.id, round_id, limit=10)

        embed = discord.Embed(
            title=f"Tur {round_id} Sonuçları",
            description=f"{trigger_text}\nTur bitti, yeni tur başladı.",
            color=discord.Color.gold(),
        )

        if not rows:
            embed.add_field(name="Durum", value="Bu turda geçerli kelime oynanmadı.")
        else:
            lines: list[str] = []
            for index, row in enumerate(rows, start=1):
                user_id = int(row["user_id"])
                points = int(row["points"])
                words = int(row["words"])
                lines.append(
                    f"{index}. <@{user_id}> - {points} puan ({words} kelime)"
                )

            embed.add_field(name="Liderlik", value="\n".join(lines), inline=False)

        await target_channel.send(embed=embed)
        await self.db.reset_round(guild.id)
        starter_word = self.word_bank.random_word()
        await self.db.seed_round_with_word(guild.id, starter_word)
        await target_channel.send(
            "Yeni turun başlangıç kelimesi: "
            f"**{starter_word}**\n"
            f"Sıradaki kelime '{starter_word[-1]}' harfi ile başlamalı."
        )

    async def _send_auto_word_after_soft_g(
        self,
        guild_id: int,
        target_channel: discord.TextChannel,
    ) -> None:
        max_attempts = min(100, max(1, self.word_bank.size))

        for _ in range(max_attempts):
            auto_word = self.word_bank.random_word()

            if auto_word[-1] == "ğ":
                continue

            try:
                await self.db.record_system_word(guild_id, auto_word)
            except ValueError:
                continue

            try:
                await target_channel.send(
                    f"**{auto_word}**\n"
                    f"Sıradaki kelime '{auto_word[-1]}' harfi ile başlamalı."
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

            return

        try:
            await target_channel.send(
                "Kelime 'ğ' ile bitti ama otomatik yeni kelime bulunamadı."
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _process_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        settings = await self.db.get_settings(message.guild.id)
        escape_prefix = str(settings["escape_prefix"]).strip()

        # Allow non-game chatter in the game channel via an escape prefix.
        if escape_prefix and message.content.strip().startswith(escape_prefix):
            return

        game_channel_id = settings["game_channel_id"]

        if game_channel_id is None or message.channel.id != game_channel_id:
            return

        state = await self.db.get_game_state(message.guild.id)
        normalized = normalize_word(message.content, min_length=2)

        if normalized is None:
            await self._handle_invalid_word(
                message,
                settings,
                "Lütfen sadece tek kelime yaz ve en az 2 harf kullan.",
            )
            return

        expected = state["expected_start_char"]
        if expected and normalized[0] != expected:
            await self._handle_invalid_word(
                message,
                settings,
                f"Kelime '{expected}' harfi ile başlamalı.",
            )
            return

        if (
            not settings["allow_consecutive_turns"]
            and state["last_player_id"] == message.author.id
            and state["words_in_round"] > 0
        ):
            await self._handle_invalid_word(
                message,
                settings,
                "Aynı kullanıcı arka arkaya oynayamaz.",
            )
            return

        if not self.word_bank.contains(normalized):
            await self._handle_invalid_word(
                message,
                settings,
                "Bu kelime listede bulunamadı.",
            )
            return

        if await self.db.is_word_used(message.guild.id, state["current_round"], normalized):
            await self._handle_invalid_word(
                message,
                settings,
                "Bu kelime bu turda zaten kullanıldı.",
            )
            return

        result = await self.db.record_valid_word(
            guild_id=message.guild.id,
            user_id=message.author.id,
            word=normalized,
            next_start_char=normalized[-1],
            points_per_word=settings["points_per_word"],
            level_up_points=settings["level_up_points"],
        )

        if settings["react_correct_words"]:
            try:
                await message.add_reaction(settings["reaction_emoji"])
            except (discord.Forbidden, discord.HTTPException):
                pass

        if int(result["level_ups"]) > 0:
            try:
                await message.channel.send(
                    f"{message.author.mention} seviye atladı! Yeni seviye: {result['level']}"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        if int(result["words_in_round"]) >= settings["reset_after_words"]:
            await self._publish_round_results_and_reset(
                guild=message.guild,
                target_channel=message.channel,
                round_id=int(result["round_id"]),
                trigger_text="Maksimum kelime sayısına ulaşıldı.",
            )
            return

        if normalized[-1] == "ğ" and isinstance(message.channel, discord.TextChannel):
            await self._send_auto_word_after_soft_g(
                guild_id=message.guild.id,
                target_channel=message.channel,
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        lock = self._guild_lock(message.guild.id)
        async with lock:
            try:
                await self._process_message(message)
            except Exception:
                LOGGER.exception("Mesaj işlenirken hata oluştu.")

    @app_commands.command(
        name="ayar_goster",
        description="Sunucu kelime oyunu ayarlarını gösterir.",
    )
    async def ayar_goster(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_guild_interaction(interaction):
            return

        settings = await self.db.get_settings(interaction.guild_id)
        embed = discord.Embed(
            title="Kelime Oyunu Ayarları",
            description=self._format_settings(settings),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="ayar_kanal",
        description="Oyunun oynanacağı kanalı ayarlar.",
    )
    @app_commands.describe(kanal="Kelime oyununun oynanacağı kanal")
    async def ayar_kanal(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel,
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "game_channel_id", kanal.id)
        await interaction.response.send_message(
            f"Oyun kanalı {kanal.mention} olarak ayarlandı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_yanlis_sil",
        description="Yanlış kelimelerin silinmesini açar veya kapatır.",
    )
    @app_commands.describe(aktif="Açık ise yanlış kelime mesajı silinir")
    async def ayar_yanlis_sil(
        self,
        interaction: discord.Interaction,
        aktif: bool,
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "delete_wrong_words", int(aktif))
        await interaction.response.send_message(
            f"Yanlış kelime silme {'açıldı' if aktif else 'kapatıldı'}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_uyari",
        description="Yanlış kelimelerde uyarı gönderimini açar veya kapatır.",
    )
    @app_commands.describe(aktif="Açık ise hata nedenini yazan uyarı gönderilir")
    async def ayar_uyari(
        self,
        interaction: discord.Interaction,
        aktif: bool,
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "send_warning", int(aktif))
        await interaction.response.send_message(
            f"Uyarı mesajı {'açıldı' if aktif else 'kapatıldı'}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_dogru_reaksiyon",
        description="Doğru kelimelere reaksiyon bırakmayı açar veya kapatır.",
    )
    @app_commands.describe(aktif="Açık ise doğru kelime mesajına reaksiyon bırakılır")
    async def ayar_dogru_reaksiyon(
        self,
        interaction: discord.Interaction,
        aktif: bool,
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(
            interaction.guild_id,
            "react_correct_words",
            int(aktif),
        )
        await interaction.response.send_message(
            f"Doğru kelime reaksiyonu {'açıldı' if aktif else 'kapatıldı'}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_reaksiyon_emoji",
        description="Doğru kelimelere bırakılacak emojiyi belirler.",
    )
    @app_commands.describe(emoji="Örnek: ✅ veya <:ozel:1234567890>")
    async def ayar_reaksiyon_emoji(
        self,
        interaction: discord.Interaction,
        emoji: app_commands.Range[str, 1, 64],
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "reaction_emoji", emoji)
        await interaction.response.send_message(
            f"Reaksiyon emojisi {emoji} olarak ayarlandı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_kacis_karakteri",
        description="Oyun dışı mesajlar için kaçış karakterini ayarlar.",
    )
    @app_commands.describe(karakter="Örnek: \\ veya !")
    async def ayar_kacis_karakteri(
        self,
        interaction: discord.Interaction,
        karakter: app_commands.Range[str, 1, 1],
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        if karakter.isspace():
            await interaction.response.send_message(
                "Kaçış karakteri boşluk olamaz.",
                ephemeral=True,
            )
            return

        await self.db.update_setting(interaction.guild_id, "escape_prefix", karakter)
        await interaction.response.send_message(
            f"Kaçış karakteri {karakter} olarak ayarlandı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_kelime_puani",
        description="Doğru kelime başına verilen puanı ayarlar.",
    )
    @app_commands.describe(puan="Her doğru kelimenin puanı")
    async def ayar_kelime_puani(
        self,
        interaction: discord.Interaction,
        puan: app_commands.Range[int, 1, 10000],
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "points_per_word", int(puan))
        await interaction.response.send_message(
            f"Kelime puanı {puan} olarak ayarlandı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_seviye_puani",
        description="Seviye atlamak için gereken puanı ayarlar.",
    )
    @app_commands.describe(puan="Bir seviye yükselmek için gereken puan")
    async def ayar_seviye_puani(
        self,
        interaction: discord.Interaction,
        puan: app_commands.Range[int, 1, 100000],
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "level_up_points", int(puan))
        await interaction.response.send_message(
            f"Seviye atlama puanı {puan} olarak ayarlandı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_sifirlama_kelimesi",
        description="Kaç kelime sonra turun sıfırlanacağını ayarlar.",
    )
    @app_commands.describe(adet="Tur bitişindeki toplam kelime sayısı")
    async def ayar_sifirlama_kelimesi(
        self,
        interaction: discord.Interaction,
        adet: app_commands.Range[int, 1, 100000],
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(interaction.guild_id, "reset_after_words", int(adet))
        await interaction.response.send_message(
            f"Tur sıfırlama sınırı {adet} kelime olarak ayarlandı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="ayar_ardisik_oyun",
        description="Aynı kişinin üst üste oynamasını açar veya kapatır.",
    )
    @app_commands.describe(aktif="Açık ise aynı kullanıcı üst üste oynayabilir")
    async def ayar_ardisik_oyun(
        self,
        interaction: discord.Interaction,
        aktif: bool,
    ) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        await self.db.update_setting(
            interaction.guild_id,
            "allow_consecutive_turns",
            int(aktif),
        )
        await interaction.response.send_message(
            f"Ardışık oyun {'açıldı' if aktif else 'kapatıldı'}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="oyun_durum",
        description="Aktif turun durumunu gösterir.",
    )
    async def oyun_durum(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_guild_interaction(interaction):
            return

        settings = await self.db.get_settings(interaction.guild_id)
        state = await self.db.get_game_state(interaction.guild_id)

        channel_text = (
            f"<#{settings['game_channel_id']}>"
            if settings["game_channel_id"]
            else "Ayarlanmadı"
        )
        expected = state["expected_start_char"] or "Serbest"

        embed = discord.Embed(title="Oyun Durumu", color=discord.Color.green())
        embed.add_field(name="Kanal", value=channel_text, inline=False)
        embed.add_field(name="Tur", value=str(state["current_round"]), inline=True)
        embed.add_field(name="Turdaki Kelime", value=str(state["words_in_round"]), inline=True)
        embed.add_field(name="Beklenen Baş Harf", value=str(expected), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="oyun_sifirla",
        description="Mevcut turu bitirir ve liderliği yayınlayarak yeni tur başlatır.",
    )
    async def oyun_sifirla(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_manage_guild(interaction):
            return

        guild = interaction.guild
        if guild is None:
            return

        settings = await self.db.get_settings(guild.id)
        configured_channel_id = settings["game_channel_id"]

        target_channel: discord.TextChannel | None = None
        if configured_channel_id is not None:
            channel = guild.get_channel(configured_channel_id)
            if isinstance(channel, discord.TextChannel):
                target_channel = channel

        if target_channel is None and isinstance(interaction.channel, discord.TextChannel):
            target_channel = interaction.channel

        if target_channel is None:
            await interaction.response.send_message(
                "Liderlik tablosunu yayınlamak için uygun bir yazı kanalı bulunamadı.",
                ephemeral=True,
            )
            return

        lock = self._guild_lock(guild.id)
        async with lock:
            state = await self.db.get_game_state(guild.id)
            await self._publish_round_results_and_reset(
                guild=guild,
                target_channel=target_channel,
                round_id=state["current_round"],
                trigger_text=f"Tur bir yönetici tarafından sıfırlandı ({interaction.user.mention}).",
            )

        await interaction.response.send_message(
            f"Tur sıfırlandı ve liderlik tablosu {target_channel.mention} kanalında paylaşıldı.",
            ephemeral=True,
        )

    @app_commands.command(
        name="seviye",
        description="Kendi seviye ve puan bilgini gösterir (sadece sana görünür).",
    )
    @app_commands.describe(kullanici="İstersen başka bir kullanıcının bilgisini de görebilirsin")
    async def seviye(
        self,
        interaction: discord.Interaction,
        kullanici: discord.Member | None = None,
    ) -> None:
        if not await self._ensure_guild_interaction(interaction):
            return

        target = kullanici or interaction.user
        if not isinstance(target, (discord.Member, discord.User)):
            target = interaction.user

        profile = await self.db.get_user_profile(interaction.guild_id, target.id)
        settings = await self.db.get_settings(interaction.guild_id)

        embed = discord.Embed(
            title=f"Seviye Bilgisi - {target.display_name if isinstance(target, discord.Member) else target.name}",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Seviye", value=str(profile["level"]), inline=True)
        embed.add_field(name="Toplam Puan", value=str(profile["total_points"]), inline=True)
        embed.add_field(name="Toplam Kelime", value=str(profile["total_words"]), inline=True)
        embed.add_field(
            name="Seviye İlerlemesi",
            value=f"{profile['level_progress']} / {settings['level_up_points']}",
            inline=False,
        )
        embed.add_field(name="Puan Sırası", value=f"#{profile['points_rank']}", inline=True)
        embed.add_field(name="Seviye Sırası", value=f"#{profile['level_rank']}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="liderlik",
        description="Sunucu liderlik tablosunu gösterir.",
    )
    @app_commands.describe(tur="Liderlik tablosu turu")
    @app_commands.choices(
        tur=[
            app_commands.Choice(name="Toplam Puan", value="puan"),
            app_commands.Choice(name="Seviye", value="seviye"),
            app_commands.Choice(name="Günlük", value="gunluk"),
            app_commands.Choice(name="Haftalık", value="haftalik"),
        ]
    )
    async def liderlik(
        self,
        interaction: discord.Interaction,
        tur: app_commands.Choice[str],
    ) -> None:
        if not await self._ensure_guild_interaction(interaction):
            return

        board_type = tur.value
        rows = await self.db.get_leaderboard(
            interaction.guild_id,
            board_type=board_type,  # type: ignore[arg-type]
            limit=10,
        )

        titles = {
            "puan": "Toplam Puan Liderliği",
            "seviye": "Seviye Liderliği",
            "gunluk": "Günlük Liderlik (24 Saat)",
            "haftalik": "Haftalık Liderlik (7 Gün)",
        }

        embed = discord.Embed(
            title=titles.get(board_type, "Liderlik"),
            color=discord.Color.orange(),
        )

        if not rows:
            embed.description = "Henüz veri yok."
        else:
            lines: list[str] = []
            for index, row in enumerate(rows, start=1):
                user_id = int(row["user_id"])
                if board_type == "seviye":
                    lines.append(
                        f"{index}. <@{user_id}> - Seviye {int(row['level'])} "
                        f"({int(row['level_progress'])} ilerleme, {int(row['total_points'])} puan)"
                    )
                else:
                    points = int(row["points"])
                    words = int(row["words"]) if "words" in row else 0
                    lines.append(
                        f"{index}. <@{user_id}> - {points} puan"
                        + (f" ({words} kelime)" if words > 0 else "")
                    )

            embed.description = "\n".join(lines)

        # Seviye komutlarını sadece komutu kullanan kişi görür.
        ephemeral = board_type == "seviye"
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(
        name="yardim",
        description="Kelime oyunu komutlarının kısa özetini gösterir.",
    )
    async def yardim(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Kelime Oyunu Yardım", color=discord.Color.teal())
        embed.description = (
            "Temel komutlar:\n"
            "- /ayar_goster\n"
            "- /ayar_kanal\n"
            "- /ayar_yanlis_sil\n"
            "- /ayar_uyari\n"
            "- /ayar_dogru_reaksiyon\n"
            "- /ayar_reaksiyon_emoji\n"
            "- /ayar_kacis_karakteri\n"
            "- /ayar_kelime_puani\n"
            "- /ayar_seviye_puani\n"
            "- /ayar_sifirlama_kelimesi\n"
            "- /ayar_ardisik_oyun\n"
            "- /oyun_durum\n"
            "- /oyun_sifirla\n"
            "- /seviye (ephemeral)\n"
            "- /liderlik"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class KelimeBot(commands.Bot):
    def __init__(self, db: Database, word_bank: WordBank) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

        self.db = db
        self.word_bank = word_bank

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.db.initialize_schema()
        await self.add_cog(WordGameCog(self, self.db, self.word_bank))
        await self.tree.sync()
        LOGGER.info("Slash komutları senkronize edildi.")

    async def on_ready(self) -> None:
        LOGGER.info("Bot hazır: %s", self.user)

    async def close(self) -> None:
        await self.db.close()
        await super().close()
