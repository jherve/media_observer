from typing import Any
import aiosqlite
import asyncio
from datetime import datetime
import numpy as np

from de_quoi_parle_le_monde.article import (
    TopArticle,
    FeaturedArticleSnapshot,
    FeaturedArticle,
)
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
    columns = {
        "featured_article_snapshots": ["id", "featured_article_id", "title", "url"],
        "articles_embeddings": [
            "id",
            "featured_article_snapshot_id",
            "title_embedding",
        ],
        "snapshot_apparitions": [
            "snapshot_id",
            "site_id",
            "site_name",
            "site_original_url",
            "timestamp",
            "timestamp_virtual",
            "featured_article_snapshot_id",
            "featured_article_id",
            "title",
            "url_archive",
            "url_article",
            "is_main",
            "rank",
        ],
    }

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
                    name TEXT,
                    original_url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS sites_unique_name
                ON sites (name);
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER REFERENCES sites (id) ON DELETE CASCADE,
                    timestamp TEXT,
                    timestamp_virtual TEXT,
                    url_original TEXT,
                    url_snapshot TEXT
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
                CREATE TABLE IF NOT EXISTS featured_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS featured_articles_unique_url
                ON featured_articles (url);
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS featured_article_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    featured_article_id INTEGER REFERENCES featured_articles (id) ON DELETE CASCADE,
                    title TEXT,
                    url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS featured_article_snapshots_unique_idx_featured_article_id_url
                ON featured_article_snapshots (featured_article_id, url);
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
                CREATE VIEW IF NOT EXISTS snapshots_view AS
                    SELECT
                        s.id,
                        si.id AS site_id,
                        si.name AS site_name,
                        si.original_url AS site_original_url,
                        s.timestamp,
                        s.timestamp_virtual
                    FROM
                        snapshots AS s
                    JOIN
                        sites AS si ON si.id = s.site_id
                """
            )

            await conn.execute(
                """
                CREATE VIEW IF NOT EXISTS main_page_apparitions AS
                    SELECT
                        fas.id,
                        fas.featured_article_id,
                        fas.title,
                        fas.url AS url_archive,
                        fa.url AS url_article,
                        m.snapshot_id AS main_in_snapshot_id,
                        t.snapshot_id AS top_in_snapshot_id,
                        t.rank
                    FROM featured_article_snapshots fas
                    JOIN featured_articles fa ON fa.id = fas.featured_article_id
                    LEFT JOIN main_articles m ON m.featured_article_snapshot_id = fas.id
                    LEFT JOIN top_articles t ON t.featured_article_snapshot_id = fas.id
                """
            )

            await conn.execute(
                """
                CREATE VIEW IF NOT EXISTS snapshot_apparitions AS
                    SELECT
                        sv.id as snapshot_id,
                        sv.site_id,
                        sv.site_name,
                        sv.site_original_url,
                        sv.timestamp,
                        sv.timestamp_virtual,
                        mpa.id AS featured_article_snapshot_id,
                        mpa.featured_article_id,
                        mpa.title,
                        mpa.url_archive,
                        mpa.url_article,
                        mpa.main_in_snapshot_id IS NOT NULL AS is_main,
                        mpa.rank
                    FROM main_page_apparitions mpa
                    JOIN snapshots_view sv ON sv.id = mpa.main_in_snapshot_id OR sv.id = mpa.top_in_snapshot_id
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS articles_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    featured_article_snapshot_id INTEGER REFERENCES featured_article_snapshots (id) ON DELETE CASCADE,
                    title_embedding BLOB
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS articles_embeddings_unique_idx_featured_article_snapshot_id
                ON articles_embeddings (featured_article_snapshot_id);
            """
            )

    async def add_site(self, name: str, original_url: str) -> int:
        return await self._insert_or_get(
            self._insert_stmt("sites", ["name", "original_url"]),
            [name, original_url],
            """
                    SELECT id
                    FROM sites
                    WHERE name = ?
                    """,
            [name],
        )

    async def add_snapshot(
        self, site_id: int, snapshot: InternetArchiveSnapshotId, virtual: datetime
    ) -> int:
        return await self._insert_or_get(
            self._insert_stmt(
                "snapshots",
                [
                    "timestamp",
                    "site_id",
                    "timestamp_virtual",
                    "url_original",
                    "url_snapshot",
                ],
            ),
            [snapshot.timestamp, site_id, virtual, snapshot.original, snapshot.url],
            """
                    SELECT id
                    FROM snapshots
                    WHERE timestamp_virtual = ? AND site_id = ?
                    """,
            [virtual, site_id],
        )

    async def add_featured_article(self, article: FeaturedArticle):
        return await self._insert_or_get(
            self._insert_stmt("featured_articles", ["url"]),
            [str(article.url)],
            """
                    SELECT id
                    FROM featured_articles
                    WHERE url = ?
                    """,
            [str(article.url)],
        )

    async def add_featured_article_snapshot(
        self, featured_article_id: int, article: FeaturedArticleSnapshot
    ):
        return await self._insert_or_get(
            self._insert_stmt(
                "featured_article_snapshots",
                ["title", "url", "featured_article_id"],
            ),
            [article.title, article.url, featured_article_id],
            """
                    SELECT id
                    FROM featured_article_snapshots
                    WHERE featured_article_id = ? AND url = ?
                    """,
            [featured_article_id, article.url],
        )

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
                    "top_articles",
                    ["snapshot_id", "featured_article_snapshot_id", "rank"],
                ),
                [snapshot_id, article_id, article.rank],
            )
            await conn.commit()

    async def exists_snapshot(self, name: str, dt: datetime):
        async with self.conn as conn:
            exists = await conn.execute_fetchall(
                """
                    SELECT 1
                    FROM snapshots snap
                    JOIN sites s ON s.id = snap.site_id
                    WHERE s.name = ? AND timestamp_virtual = ?
                """,
                [name, dt],
            )

            return exists != []

    async def list_all_featured_article_snapshots(self):
        async with self.conn as conn:
            rows = await conn.execute_fetchall(
                """
                    SELECT *
                    FROM featured_article_snapshots
                """,
            )

            return [self._from_row(r, "featured_article_snapshots") for r in rows]

    async def list_snapshot_apparitions(self, featured_article_snapshot_ids: list[int]):
        async with self.conn as conn:
            placeholders = ", ".join(["?" for _ in featured_article_snapshot_ids])
            rows = await conn.execute_fetchall(
                f"""
                    SELECT *
                    FROM snapshot_apparitions
                    WHERE featured_article_snapshot_id IN ({placeholders})
                """,
                featured_article_snapshot_ids,
            )

            return [self._from_row(r, "snapshot_apparitions") for r in rows]

    @classmethod
    def _from_row(cls, r, table_or_view: str):
        columns = cls.columns[table_or_view]

        return {col: r[idx] for idx, col in enumerate(columns)}

    async def list_all_embedded_featured_article_snapshot_ids(self) -> list[int]:
        async with self.conn as conn:
            rows = await conn.execute_fetchall(
                """
                    SELECT featured_article_snapshot_id
                    FROM articles_embeddings
                """,
            )

            return [r[0] for r in rows]

    async def list_all_articles_embeddings(self):
        async with self.conn as conn:
            rows = await conn.execute_fetchall(
                """
                    SELECT *
                    FROM articles_embeddings
                """,
            )

            return [self._from_articles_embeddings_row(r) for r in rows]

    async def get_article_embedding(self, featured_article_snapshot_ids: list[int]):
        async with self.conn as conn:
            placeholders = ", ".join(["?" for _ in featured_article_snapshot_ids])
            rows = await conn.execute_fetchall(
                f"""
                    SELECT *
                    FROM articles_embeddings
                    WHERE featured_article_snapshot_id IN ({placeholders})
                """,
                featured_article_snapshot_ids,
            )

            return [self._from_articles_embeddings_row(r) for r in rows]

    @classmethod
    def _from_articles_embeddings_row(cls, r):
        d = cls._from_row(r, "articles_embeddings")
        d.update(title_embedding=np.frombuffer(d["title_embedding"], dtype="float32"))

        return d

    async def add_embedding(self, featured_article_snapshot_id: int, embedding):
        async with self.conn as conn:
            await conn.execute_insert(
                self._insert_stmt(
                    "articles_embeddings",
                    ["featured_article_snapshot_id", "title_embedding"],
                ),
                [featured_article_snapshot_id, embedding],
            )
            await conn.commit()

    async def list_sites(self):
        async with self.conn as conn:
            sites = await conn.execute_fetchall("SELECT * FROM sites")
            return [{"id": s[0], "original_url": s[1], "name": s[2]} for s in sites]

    async def list_neighbouring_main_articles(
        self,
        site_id: int,
        featured_article_snapshot_id: int | None = None,
    ):
        async with self.conn as conn:
            if featured_article_snapshot_id is None:
                timestamp_query, timestamp_params = (
                    """
                    SELECT timestamp_virtual
                    FROM snapshot_apparitions sav
                    WHERE is_main AND site_id = ?
                    ORDER BY timestamp_virtual DESC
                    LIMIT 1
                    """,
                    [site_id],
                )
            else:
                timestamp_query, timestamp_params = (
                    """
                    SELECT timestamp_virtual
                    FROM snapshot_apparitions sav
                    WHERE is_main AND site_id = ? AND featured_article_snapshot_id = ?
                    """,
                    [site_id, featured_article_snapshot_id],
                )

            # This query is the union of 3 queries that respectively fetch :
            #   * articles published at the same time as the queried article (including the queried article)
            #   * the article published just after, on the same site
            #   *the article published just before, on the same site
            main_articles = await conn.execute_fetchall(
                f"""
                WITH original_timestamp AS (
                    {timestamp_query}
                ), sav_diff AS (
                    SELECT sav.*, unixepoch(sav.timestamp_virtual) - unixepoch((SELECT * FROM original_timestamp)) AS time_diff
                    FROM snapshot_apparitions sav
                )
                SELECT * FROM (
                    SELECT * FROM sav_diff
                    WHERE is_main AND time_diff = 0
                )
                UNION ALL
                SELECT * FROM (
                    SELECT * FROM sav_diff
                    WHERE is_main AND site_id = ? AND time_diff > 0
                    ORDER BY time_diff
                    LIMIT 1
                )
                UNION ALL
                SELECT * FROM (
                    SELECT * FROM sav_diff
                    WHERE is_main AND site_id = ? AND time_diff < 0
                    ORDER BY time_diff DESC
                    LIMIT 1
                )
                """,
                timestamp_params + [site_id, site_id],
            )

            return [
                self._from_row(a, "snapshot_apparitions") | {"time_diff": a[13]}
                for a in main_articles
            ]

    async def select_from(self, table):
        async with self.conn as conn:
            return await conn.execute_fetchall(
                f"""
                    SELECT *
                    FROM {table}
                """,
            )

    async def _insert_or_get(
        self,
        insert_stmt: str,
        insert_args: list[Any],
        select_stmt: str,
        select_args: list[Any],
    ) -> int:
        async with self.conn as conn:
            (id_,) = await conn.execute_insert(insert_stmt, insert_args)

            if id_ == 0:
                [(id_,)] = await conn.execute_fetchall(select_stmt, select_args)

            await conn.commit()
            return id_

    @staticmethod
    def _insert_stmt(table, cols):
        cols_str = ", ".join(cols)
        placeholders = ", ".join(("?" for c in cols))
        return f"""
            INSERT INTO {table} ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING;
        """
