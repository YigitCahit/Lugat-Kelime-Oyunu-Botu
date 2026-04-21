from __future__ import annotations

from typing import Any, Literal

import aiomysql

from .config import MySQLConfig

LeaderboardType = Literal["puan", "seviye", "gunluk", "haftalik"]


class Database:
    def __init__(self, config: MySQLConfig) -> None:
        self.config = config
        self.pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        self.pool = await aiomysql.create_pool(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            db=self.config.database,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=10,
        )

    async def close(self) -> None:
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    def _require_pool(self) -> aiomysql.Pool:
        if self.pool is None:
            raise RuntimeError("Veritabani havuzu hazir degil.")
        return self.pool

    async def initialize_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id BIGINT PRIMARY KEY,
                game_channel_id BIGINT NULL,
                delete_wrong_words BOOLEAN NOT NULL DEFAULT TRUE,
                send_warning BOOLEAN NOT NULL DEFAULT TRUE,
                react_correct_words BOOLEAN NOT NULL DEFAULT TRUE,
                escape_prefix VARCHAR(8) NOT NULL DEFAULT '\\\\',
                reaction_emoji VARCHAR(64) NOT NULL DEFAULT '✅',
                points_per_word INT NOT NULL DEFAULT 5,
                level_up_points INT NOT NULL DEFAULT 100,
                reset_after_words INT NOT NULL DEFAULT 50,
                allow_consecutive_turns BOOLEAN NOT NULL DEFAULT FALSE,
                privileged_role_id BIGINT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS game_state (
                guild_id BIGINT PRIMARY KEY,
                current_round INT NOT NULL DEFAULT 1,
                words_in_round INT NOT NULL DEFAULT 0,
                expected_start_char VARCHAR(8) NULL,
                last_word VARCHAR(64) NULL,
                last_player_id BIGINT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS user_stats (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                total_points BIGINT NOT NULL DEFAULT 0,
                total_words BIGINT NOT NULL DEFAULT 0,
                level INT NOT NULL DEFAULT 1,
                level_progress BIGINT NOT NULL DEFAULT 0,
                last_played_at TIMESTAMP NULL,
                PRIMARY KEY (guild_id, user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS word_entries (
                id BIGINT NOT NULL AUTO_INCREMENT,
                guild_id BIGINT NOT NULL,
                round_id INT NOT NULL,
                user_id BIGINT NOT NULL,
                word VARCHAR(64) NOT NULL,
                points INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uq_guild_round_word (guild_id, round_id, word),
                INDEX idx_guild_created (guild_id, created_at),
                INDEX idx_guild_round (guild_id, round_id),
                INDEX idx_guild_user (guild_id, user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        ]

        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for statement in statements:
                    await cursor.execute(statement)

                # Backward-compatible migration for deployments created before escape_prefix existed.
                await cursor.execute("SHOW COLUMNS FROM guild_settings LIKE 'escape_prefix'")
                column = await cursor.fetchone()
                if column is None:
                    await cursor.execute(
                        """
                        ALTER TABLE guild_settings
                        ADD COLUMN escape_prefix VARCHAR(8) NOT NULL DEFAULT '\\\\'
                        AFTER react_correct_words
                        """
                    )

                await cursor.execute("SHOW COLUMNS FROM guild_settings LIKE 'privileged_role_id'")
                column = await cursor.fetchone()
                if column is None:
                    await cursor.execute(
                        """
                        ALTER TABLE guild_settings
                        ADD COLUMN privileged_role_id BIGINT NULL
                        AFTER allow_consecutive_turns
                        """
                    )

    async def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()

    async def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return list(await cursor.fetchall())

    async def _execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                affected = await cursor.execute(query, params)
                return int(affected)

    async def ensure_guild(self, guild_id: int) -> None:
        await self._execute(
            "INSERT IGNORE INTO guild_settings (guild_id) VALUES (%s)",
            (guild_id,),
        )
        await self._execute(
            "INSERT IGNORE INTO game_state (guild_id) VALUES (%s)",
            (guild_id,),
        )

    async def get_settings(self, guild_id: int) -> dict[str, Any]:
        await self.ensure_guild(guild_id)
        row = await self._fetchone(
            "SELECT * FROM guild_settings WHERE guild_id = %s",
            (guild_id,),
        )
        if row is None:
            raise RuntimeError("Sunucu ayarlari okunamadi.")

        return {
            "guild_id": int(row["guild_id"]),
            "game_channel_id": int(row["game_channel_id"]) if row["game_channel_id"] else None,
            "delete_wrong_words": bool(row["delete_wrong_words"]),
            "send_warning": bool(row["send_warning"]),
            "react_correct_words": bool(row["react_correct_words"]),
            "escape_prefix": str(row.get("escape_prefix") or "\\"),
            "reaction_emoji": str(row["reaction_emoji"]),
            "points_per_word": int(row["points_per_word"]),
            "level_up_points": int(row["level_up_points"]),
            "reset_after_words": int(row["reset_after_words"]),
            "allow_consecutive_turns": bool(row["allow_consecutive_turns"]),
            "privileged_role_id": int(row["privileged_role_id"]) if row["privileged_role_id"] else None,
        }

    async def update_setting(self, guild_id: int, column: str, value: Any) -> None:
        allowed_columns = {
            "game_channel_id",
            "delete_wrong_words",
            "send_warning",
            "react_correct_words",
            "escape_prefix",
            "reaction_emoji",
            "points_per_word",
            "level_up_points",
            "reset_after_words",
            "allow_consecutive_turns",
            "privileged_role_id",
        }

        if column not in allowed_columns:
            raise ValueError(f"Gecersiz ayar alani: {column}")

        await self.ensure_guild(guild_id)
        await self._execute(
            f"UPDATE guild_settings SET {column} = %s WHERE guild_id = %s",
            (value, guild_id),
        )

    async def get_game_state(self, guild_id: int) -> dict[str, Any]:
        await self.ensure_guild(guild_id)
        row = await self._fetchone(
            "SELECT * FROM game_state WHERE guild_id = %s",
            (guild_id,),
        )
        if row is None:
            raise RuntimeError("Oyun durumu okunamadi.")

        return {
            "guild_id": int(row["guild_id"]),
            "current_round": int(row["current_round"]),
            "words_in_round": int(row["words_in_round"]),
            "expected_start_char": row["expected_start_char"],
            "last_word": row["last_word"],
            "last_player_id": int(row["last_player_id"]) if row["last_player_id"] else None,
        }

    async def is_word_used(self, guild_id: int, round_id: int, word: str) -> bool:
        row = await self._fetchone(
            """
            SELECT id
            FROM word_entries
            WHERE guild_id = %s AND round_id = %s AND word = %s
            LIMIT 1
            """,
            (guild_id, round_id, word),
        )
        return row is not None

    async def record_valid_word(
        self,
        guild_id: int,
        user_id: int,
        word: str,
        next_start_char: str,
        points_per_word: int,
        level_up_points: int,
    ) -> dict[str, Any]:
        await self.ensure_guild(guild_id)
        pool = self._require_pool()

        async with pool.acquire() as conn:
            try:
                await conn.begin()
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT current_round, words_in_round FROM game_state WHERE guild_id = %s FOR UPDATE",
                        (guild_id,),
                    )
                    state = await cursor.fetchone()
                    if state is None:
                        raise RuntimeError("Oyun durumu bulunamadi.")

                    round_id = int(state["current_round"])
                    words_in_round = int(state["words_in_round"]) + 1

                    await cursor.execute(
                        """
                        INSERT INTO word_entries (guild_id, round_id, user_id, word, points)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (guild_id, round_id, user_id, word, points_per_word),
                    )

                    await cursor.execute(
                        """
                        INSERT INTO user_stats (
                            guild_id, user_id, total_points, total_words, level, level_progress, last_played_at
                        )
                        VALUES (%s, %s, %s, 1, 1, %s, UTC_TIMESTAMP())
                        ON DUPLICATE KEY UPDATE
                            total_points = total_points + %s,
                            total_words = total_words + 1,
                            level_progress = level_progress + %s,
                            last_played_at = UTC_TIMESTAMP()
                        """,
                        (
                            guild_id,
                            user_id,
                            points_per_word,
                            points_per_word,
                            points_per_word,
                            points_per_word,
                        ),
                    )

                    await cursor.execute(
                        """
                        SELECT level, level_progress, total_points, total_words
                        FROM user_stats
                        WHERE guild_id = %s AND user_id = %s
                        FOR UPDATE
                        """,
                        (guild_id, user_id),
                    )
                    stats = await cursor.fetchone()
                    if stats is None:
                        raise RuntimeError("Kullanici istatistigi okunamadi.")

                    level = int(stats["level"])
                    level_progress = int(stats["level_progress"])
                    total_points = int(stats["total_points"])
                    total_words = int(stats["total_words"])

                    level_ups = 0
                    while level_progress >= level_up_points:
                        level += 1
                        level_progress -= level_up_points
                        level_ups += 1

                    if level_ups > 0:
                        await cursor.execute(
                            """
                            UPDATE user_stats
                            SET level = %s, level_progress = %s
                            WHERE guild_id = %s AND user_id = %s
                            """,
                            (level, level_progress, guild_id, user_id),
                        )

                    await cursor.execute(
                        """
                        UPDATE game_state
                        SET words_in_round = %s,
                            expected_start_char = %s,
                            last_word = %s,
                            last_player_id = %s
                        WHERE guild_id = %s
                        """,
                        (words_in_round, next_start_char, word, user_id, guild_id),
                    )

                await conn.commit()
            except aiomysql.IntegrityError as error:
                await conn.rollback()
                raise ValueError("Bu kelime bu turda zaten kullanildi.") from error
            except Exception:
                await conn.rollback()
                raise

        return {
            "round_id": round_id,
            "words_in_round": words_in_round,
            "level": level,
            "level_progress": level_progress,
            "total_points": total_points,
            "total_words": total_words,
            "level_ups": level_ups,
        }

    async def reset_round(self, guild_id: int) -> int:
        await self.ensure_guild(guild_id)
        pool = self._require_pool()

        async with pool.acquire() as conn:
            try:
                await conn.begin()
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT current_round FROM game_state WHERE guild_id = %s FOR UPDATE",
                        (guild_id,),
                    )
                    row = await cursor.fetchone()
                    if row is None:
                        raise RuntimeError("Oyun durumu bulunamadi.")

                    new_round = int(row["current_round"]) + 1

                    await cursor.execute(
                        """
                        UPDATE game_state
                        SET current_round = %s,
                            words_in_round = 0,
                            expected_start_char = NULL,
                            last_word = NULL,
                            last_player_id = NULL
                        WHERE guild_id = %s
                        """,
                        (new_round, guild_id),
                    )

                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

        return new_round

    async def seed_round_with_word(self, guild_id: int, word: str) -> dict[str, Any]:
        await self.ensure_guild(guild_id)
        pool = self._require_pool()

        async with pool.acquire() as conn:
            try:
                await conn.begin()
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT current_round, words_in_round FROM game_state WHERE guild_id = %s FOR UPDATE",
                        (guild_id,),
                    )
                    state = await cursor.fetchone()
                    if state is None:
                        raise RuntimeError("Oyun durumu bulunamadi.")

                    if int(state["words_in_round"]) > 0:
                        raise ValueError("Tur zaten baslamis durumda.")

                    round_id = int(state["current_round"])

                    await cursor.execute(
                        """
                        INSERT INTO word_entries (guild_id, round_id, user_id, word, points)
                        VALUES (%s, %s, 0, %s, 0)
                        """,
                        (guild_id, round_id, word),
                    )

                    await cursor.execute(
                        """
                        UPDATE game_state
                        SET words_in_round = 0,
                            expected_start_char = %s,
                            last_word = %s,
                            last_player_id = NULL
                        WHERE guild_id = %s
                        """,
                        (word[-1], word, guild_id),
                    )

                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

        return {
            "round_id": round_id,
            "expected_start_char": word[-1],
        }

    async def record_system_word(self, guild_id: int, word: str) -> dict[str, Any]:
        await self.ensure_guild(guild_id)
        pool = self._require_pool()

        async with pool.acquire() as conn:
            try:
                await conn.begin()
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT current_round, words_in_round FROM game_state WHERE guild_id = %s FOR UPDATE",
                        (guild_id,),
                    )
                    state = await cursor.fetchone()
                    if state is None:
                        raise RuntimeError("Oyun durumu bulunamadi.")

                    round_id = int(state["current_round"])
                    words_in_round = int(state["words_in_round"])

                    await cursor.execute(
                        """
                        INSERT INTO word_entries (guild_id, round_id, user_id, word, points)
                        VALUES (%s, %s, 0, %s, 0)
                        """,
                        (guild_id, round_id, word),
                    )

                    await cursor.execute(
                        """
                        UPDATE game_state
                        SET words_in_round = %s,
                            expected_start_char = %s,
                            last_word = %s,
                            last_player_id = NULL
                        WHERE guild_id = %s
                        """,
                        (words_in_round, word[-1], word, guild_id),
                    )

                await conn.commit()
            except aiomysql.IntegrityError as error:
                await conn.rollback()
                raise ValueError("Bu kelime bu turda zaten kullanildi.") from error
            except Exception:
                await conn.rollback()
                raise

        return {
            "round_id": round_id,
            "words_in_round": words_in_round,
            "expected_start_char": word[-1],
        }

    async def get_round_leaderboard(
        self,
        guild_id: int,
        round_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT user_id, SUM(points) AS points, COUNT(*) AS words
            FROM word_entries
            WHERE guild_id = %s AND round_id = %s AND user_id <> 0
            GROUP BY user_id
            ORDER BY points DESC, words DESC, user_id ASC
            LIMIT %s
            """,
            (guild_id, round_id, limit),
        )

    async def get_leaderboard(
        self,
        guild_id: int,
        board_type: LeaderboardType,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if board_type == "puan":
            return await self._fetchall(
                """
                SELECT user_id, total_points AS points, total_words AS words
                FROM user_stats
                WHERE guild_id = %s
                ORDER BY total_points DESC, total_words DESC, user_id ASC
                LIMIT %s
                """,
                (guild_id, limit),
            )

        if board_type == "seviye":
            return await self._fetchall(
                """
                SELECT user_id, level, level_progress, total_points
                FROM user_stats
                WHERE guild_id = %s
                ORDER BY level DESC, level_progress DESC, total_points DESC, user_id ASC
                LIMIT %s
                """,
                (guild_id, limit),
            )

        if board_type == "gunluk":
            return await self._fetchall(
                """
                SELECT user_id, SUM(points) AS points, COUNT(*) AS words
                FROM word_entries
                WHERE guild_id = %s
                                    AND user_id <> 0
                  AND created_at >= UTC_TIMESTAMP() - INTERVAL 1 DAY
                GROUP BY user_id
                ORDER BY points DESC, words DESC, user_id ASC
                LIMIT %s
                """,
                (guild_id, limit),
            )

        if board_type == "haftalik":
            return await self._fetchall(
                """
                SELECT user_id, SUM(points) AS points, COUNT(*) AS words
                FROM word_entries
                WHERE guild_id = %s
                                    AND user_id <> 0
                  AND created_at >= UTC_TIMESTAMP() - INTERVAL 7 DAY
                GROUP BY user_id
                ORDER BY points DESC, words DESC, user_id ASC
                LIMIT %s
                """,
                (guild_id, limit),
            )

        raise ValueError(f"Gecersiz liderlik turu: {board_type}")

    async def get_user_profile(self, guild_id: int, user_id: int) -> dict[str, Any]:
        row = await self._fetchone(
            """
            SELECT total_points, total_words, level, level_progress
            FROM user_stats
            WHERE guild_id = %s AND user_id = %s
            """,
            (guild_id, user_id),
        )

        if row is None:
            points = 0
            words = 0
            level = 1
            level_progress = 0
        else:
            points = int(row["total_points"])
            words = int(row["total_words"])
            level = int(row["level"])
            level_progress = int(row["level_progress"])

        points_rank_row = await self._fetchone(
            """
            SELECT COUNT(*) AS c
            FROM user_stats
            WHERE guild_id = %s AND total_points > %s
            """,
            (guild_id, points),
        )
        level_rank_row = await self._fetchone(
            """
            SELECT COUNT(*) AS c
            FROM user_stats
            WHERE guild_id = %s
              AND (
                  level > %s
                  OR (level = %s AND level_progress > %s)
                  OR (level = %s AND level_progress = %s AND total_points > %s)
              )
            """,
            (guild_id, level, level, level_progress, level, level_progress, points),
        )

        points_rank = int(points_rank_row["c"]) + 1 if points_rank_row else 1
        level_rank = int(level_rank_row["c"]) + 1 if level_rank_row else 1

        return {
            "user_id": user_id,
            "total_points": points,
            "total_words": words,
            "level": level,
            "level_progress": level_progress,
            "points_rank": points_rank,
            "level_rank": level_rank,
        }
