import aiosqlite
import asyncio
from datetime import datetime

from de_quoi_parle_le_monde.article import MainArticle, TopArticle, FeaturedArticleSnapshot
from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshotId


class DbConnection:
    def __init__(self, conn_str):
        self.connection_string = conn_str
        self.semaphore = asyncio.Semaphore(1)
        self.conn = None

    async def __aenter__(self):
        await self.semaphore.acquire()
        self.conn = await aiosqlite.connect(self.connection_string)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.conn.close()
        self.conn = None
        self.semaphore.release()

    async def execute(self, *args, **kwargs):
        return await self.conn.execute(*args, **kwargs)

    async def execute_fetchall(self, *args, **kwargs):
        return await self.conn.execute_fetchall(*args, **kwargs)

    async def execute_insert(self, *args, **kwargs):
        return await self.conn.execute_insert(*args, **kwargs)

    async def commit(self):
        return await self.conn.commit()


class Storage:
    def __init__(self):
        self.conn = DbConnection("test.db")

    @staticmethod
    async def create():
        storage = Storage()
        await storage._create_db()
        return storage

    async def _create_db(self):
        async with self.conn as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS sites_unique_original_url
                ON sites (original_url);
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER REFERENCES sites (id) ON DELETE CASCADE,
                    timestamp TEXT,
                    timestamp_virtual TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS snapshots_unique_timestamp_virtual_site_id
                ON snapshots (timestamp_virtual, site_id);
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS featured_article_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    url TEXT,
                    original_url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS featured_article_snapshots_unique_idx_title_url
                ON featured_article_snapshots (title, url);
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS main_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER REFERENCES snapshots (id) ON DELETE CASCADE,
                    featured_article_snapshot_id INTEGER REFERENCES featured_article_snapshots (id) ON DELETE CASCADE
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
                    featured_article_snapshot_id INTEGER REFERENCES featured_article_snapshots (id) ON DELETE CASCADE,
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

            await conn.execute(
                """
                CREATE VIEW IF NOT EXISTS main_articles_view AS
                    SELECT
                        si.id AS site_id,
                        s.id AS snapshot_id,
                        fas.id AS featured_article_snapshot_id,
                        si.original_url AS original_url,
                        s.timestamp_virtual,
                        fas.title,
                        fas.url
                    FROM
                        main_articles as m
                    JOIN
                        snapshots AS s ON s.id = m.snapshot_id
                    JOIN
                        sites AS si ON si.id = s.site_id
                    JOIN
                        featured_article_snapshots AS fas ON m.featured_article_snapshot_id = fas.id
                """
            )

            await conn.execute(
                """
                CREATE VIEW IF NOT EXISTS top_articles_view AS
                    SELECT
                        si.id AS site_id,
                        s.id AS snapshot_id,
                        fas.id AS featured_article_snapshot_id,
                        si.original_url AS original_url,
                        s.timestamp_virtual,
                        fas.title,
                        fas.url,
                        t.rank
                    FROM
                        top_articles as t
                    JOIN
                        snapshots AS s ON s.id = t.snapshot_id
                    JOIN
                        sites AS si ON si.id = s.site_id
                    JOIN
                        featured_article_snapshots AS fas ON t.featured_article_snapshot_id = fas.id
                """
            )

    async def add_site(self, original_url: str) -> int:
        async with self.conn as conn:
            (id_,) = await conn.execute_insert(
                self._insert_stmt("sites", ["original_url"]),
                [original_url],
            )

            if id_ == 0:
                [(id_,)] = await conn.execute_fetchall(
                    """
                    SELECT id
                    FROM sites
                    WHERE original_url = ?
                    """,
                    [original_url],
                )

            await conn.commit()
            return id_

    async def add_snapshot(
        self, site_id: int, snapshot: InternetArchiveSnapshotId, virtual: datetime
    ) -> int:
        async with self.conn as conn:
            (id_,) = await conn.execute_insert(
                self._insert_stmt(
                    "snapshots", ["timestamp", "site_id", "timestamp_virtual"]
                ),
                [snapshot.timestamp, site_id, virtual],
            )

            if id_ == 0:
                [(id_,)] = await conn.execute_fetchall(
                    """
                    SELECT id
                    FROM snapshots
                    WHERE timestamp_virtual = ? AND site_id = ?
                    """,
                    [virtual, site_id],
                )

            await conn.commit()
            return id_

    async def add_featured_article_snapshot(self, article: FeaturedArticleSnapshot):
        async with self.conn as conn:
            (id_,) = await conn.execute_insert(
                self._insert_stmt("featured_article_snapshots", ["title", "url", "original_url"]),
                [article.title, article.url, str(article.original.url)],
            )

            if id_ == 0:
                [(id_,)] = await conn.execute_fetchall(
                    """
                    SELECT id
                    FROM featured_article_snapshots
                    WHERE title = ? AND url = ?
                    """,
                    [article.title, article.url],
                )

            await conn.commit()
            return id_

    async def add_main_article(self, snapshot_id: int, article_id: int):
        async with self.conn as conn:
            await conn.execute_insert(
                self._insert_stmt(
                    "main_articles", ["snapshot_id", "featured_article_snapshot_id"]
                ),
                [snapshot_id, article_id],
            )
            await conn.commit()

    async def add_top_article(
        self, snapshot_id: int, article_id: int, article: TopArticle
    ):
        async with self.conn as conn:
            await conn.execute_insert(
                self._insert_stmt(
                    "top_articles", ["snapshot_id", "featured_article_snapshot_id", "rank"]
                ),
                [snapshot_id, article_id, article.rank],
            )
            await conn.commit()

    async def select_from(self, table):
        async with self.conn as conn:
            return await conn.execute_fetchall(
                f"""
                    SELECT *
                    FROM {table}
                """,
            )

    @staticmethod
    def _insert_stmt(table, cols):
        cols_str = ", ".join(cols)
        placeholders = ", ".join(("?" for c in cols))
        return f"""
            INSERT INTO {table} ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING;
        """
