import aiosqlite
from datetime import datetime

from de_quoi_parle_le_monde.article import MainArticle, TopArticle
from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshotId


class Storage:
    def __init__(self):
        self.conn_str = "test.db"

    @staticmethod
    async def create():
        storage = Storage()
        await storage._create_db()
        return storage

    async def _create_db(self):
        async with aiosqlite.connect(self.conn_str) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    timestamp_virtual TEXT,
                    site TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS snapshots_unique_timestamp_virtual_site
                ON snapshots (timestamp_virtual, site);
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS main_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER REFERENCES snapshots (id) ON DELETE CASCADE,
                    title TEXT,
                    url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS main_articles_unique_idx_snapshot_id
                ON main_articles (snapshot_id);
            """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS top_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER REFERENCES snapshots (id) ON DELETE CASCADE,
                    title TEXT,
                    url TEXT,
                    rank INTEGER
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS top_articles_unique_idx_snapshot_id_rank
                ON top_articles (snapshot_id, rank);
                """
            )

    async def add_snapshot(
        self, snapshot: InternetArchiveSnapshotId, virtual: datetime
    ) -> int:
        async with aiosqlite.connect(self.conn_str) as conn:
            (id_,) = await conn.execute_insert(
                """
                INSERT INTO snapshots (timestamp, site, timestamp_virtual)
                VALUES (?, ?, ?)
                ON CONFLICT DO NOTHING;
                """,
                [snapshot.timestamp, snapshot.original, virtual],
            )

            if id_ == 0:
                [(id_,)] = await conn.execute_fetchall(
                    """
                    SELECT id
                    FROM snapshots
                    WHERE timestamp_virtual = ? AND site = ?
                    """,
                    [virtual, snapshot.original],
                )

            await conn.commit()
            return id_

    async def add_main_article(self, snapshot_id: int, article: MainArticle):
        async with aiosqlite.connect(self.conn_str) as conn:
            await conn.execute_insert(
                """
                INSERT INTO main_articles (snapshot_id, title, url)
                VALUES (?, ?, ?)
                ON CONFLICT DO NOTHING;
                """,
                [snapshot_id, article.title, article.url],
            )
            await conn.commit()

    async def add_top_article(self, snapshot_id: int, article: TopArticle):
        async with aiosqlite.connect(self.conn_str) as conn:
            await conn.execute_insert(
                """
                INSERT INTO top_articles (snapshot_id, title, url, rank)
                VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING;
                """,
                [snapshot_id, article.title, article.url, article.rank],
            )
            await conn.commit()
