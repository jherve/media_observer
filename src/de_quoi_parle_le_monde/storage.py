from typing import Any
from datetime import datetime
import numpy as np
from attrs import frozen
from yarl import URL

from config import settings
from de_quoi_parle_le_monde.article import (
    TopArticle,
    FeaturedArticleSnapshot,
    FeaturedArticle,
)
from de_quoi_parle_le_monde.db.sqlite import DbConnectionSQLite
from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshotId


@frozen
class UniqueIndex:
    name: str
    table: str
    columns: list[str]

    async def create_if_not_exists(self, conn):
        cols = ",".join(self.columns)
        stmt = f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self.name}
            ON {self.table} ({cols})
        """
        await conn.execute(stmt)


@frozen
class Column:
    name: str
    attrs: str


@frozen
class Table:
    name: str
    columns: list[Column]

    @property
    def column_names(self):
        return [c.name for c in self.columns]

    async def create_if_not_exists(self, conn):
        cols = ",\n".join([f"{c.name} {c.attrs}" for c in self.columns])
        await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.name} (
                    {cols}
                )
            """)


@frozen
class View:
    name: str
    create_stmt: str
    column_names: list[str]

    async def create_if_not_exists(self, conn):
        stmt = f"""
        CREATE VIEW IF NOT EXISTS {self.name} AS
        {self.create_stmt}
        """
        await conn.execute(stmt)


class Storage:
    tables = [
        Table(
            name="sites",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(name="name", attrs="TEXT"),
                Column(name="original_url", attrs="TEXT"),
            ],
        ),
        Table(
            name="snapshots",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(
                    name="site_id",
                    attrs="INTEGER REFERENCES sites (id) ON DELETE CASCADE",
                ),
                Column(name="timestamp", attrs="TEXT"),
                Column(name="timestamp_virtual", attrs="TEXT"),
                Column(name="url_original", attrs="TEXT"),
                Column(name="url_snapshot", attrs="TEXT"),
            ],
        ),
        Table(
            name="featured_articles",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(name="url", attrs="TEXT"),
            ],
        ),
        Table(
            name="featured_article_snapshots",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(
                    name="featured_article_id",
                    attrs="INTEGER REFERENCES featured_articles (id) ON DELETE CASCADE",
                ),
                Column(name="title", attrs="TEXT"),
                Column(name="url", attrs="TEXT"),
            ],
        ),
        Table(
            name="main_articles",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(
                    name="snapshot_id",
                    attrs="INTEGER REFERENCES snapshots (id) ON DELETE CASCADE",
                ),
                Column(
                    name="featured_article_snapshot_id",
                    attrs="INTEGER REFERENCES featured_article_snapshots (id) ON DELETE CASCADE",
                ),
            ],
        ),
        Table(
            name="top_articles",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(
                    name="snapshot_id",
                    attrs="INTEGER REFERENCES snapshots (id) ON DELETE CASCADE",
                ),
                Column(
                    name="featured_article_snapshot_id",
                    attrs="INTEGER REFERENCES featured_article_snapshots (id) ON DELETE CASCADE",
                ),
                Column(name="rank", attrs="INTEGER"),
            ],
        ),
        Table(
            name="articles_embeddings",
            columns=[
                Column(name="id", attrs="INTEGER PRIMARY KEY AUTOINCREMENT"),
                Column(
                    name="featured_article_snapshot_id",
                    attrs="INTEGER REFERENCES featured_article_snapshots (id) ON DELETE CASCADE",
                ),
                Column(name="title_embedding", attrs="BLOB"),
            ],
        ),
    ]

    views = [
        View(
            name="snapshots_view",
            column_names=[
                "id",
                "site_id",
                "site_name",
                "site_original_url",
                "timestamp",
                "timestamp_virtual",
            ],
            create_stmt="""
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
                """,
        ),
        View(
            name="main_page_apparitions",
            column_names=[
                "id",
                "featured_article_id",
                "title",
                "url_archive",
                "url_article",
                "main_in_snapshot_id",
                "top_in_snapshot_id",
                "rank",
            ],
            create_stmt="""
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
                """,
        ),
        View(
            name="snapshot_apparitions",
            column_names=[
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
            create_stmt="""
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
                """,
        ),
    ]

    indexes = [
        UniqueIndex(
            name="sites_unique_name",
            table="sites",
            columns=["name"],
        ),
        UniqueIndex(
            name="snapshots_unique_timestamp_virtual_site_id",
            table="snapshots",
            columns=["timestamp_virtual", "site_id"],
        ),
        UniqueIndex(
            name="main_articles_unique_idx_snapshot_id",
            table="main_articles",
            columns=["snapshot_id"],
        ),
        UniqueIndex(
            name="featured_articles_unique_url",
            table="featured_articles",
            columns=["url"],
        ),
        UniqueIndex(
            name="featured_article_snapshots_unique_idx_featured_article_id_url",
            table="featured_article_snapshots",
            columns=["featured_article_id", "url"],
        ),
        UniqueIndex(
            name="top_articles_unique_idx_snapshot_id_rank",
            table="top_articles",
            columns=["snapshot_id", "rank"],
        ),
        UniqueIndex(
            name="articles_embeddings_unique_idx_featured_article_snapshot_id",
            table="articles_embeddings",
            columns=["featured_article_snapshot_id"],
        ),
    ]

    def __init__(self):
        # We try to reproduce the scheme used by SQLAlchemy for Database-URLs
        # https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
        conn_url = URL(settings.database_url)

        if conn_url.scheme == "sqlite":
            if conn_url.path.startswith("//"):
                raise ValueError("Absolute URLs not supported for sqlite")
            elif conn_url.path.startswith("/"):
                self.conn = DbConnectionSQLite(conn_url.path[1:])
        else:
            raise ValueError("Only the SQLite backend is supported")

    @staticmethod
    async def create():
        storage = Storage()
        await storage._create_db()
        return storage

    async def _create_db(self):
        async with self.conn as conn:
            for t in self.tables:
                await t.create_if_not_exists(conn)

            for i in self.indexes:
                await i.create_if_not_exists(conn)

            for v in self.views:
                await v.create_if_not_exists(conn)

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

            return [
                self._from_row(r, self._table_by_name["featured_article_snapshots"])
                for r in rows
            ]

    async def list_snapshot_apparitions(self, featured_article_snapshot_ids: list[int]):
        if len(featured_article_snapshot_ids) == 0:
            return []

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

            return [
                self._from_row(r, self._view_by_name["snapshot_apparitions"])
                for r in rows
            ]

    @classmethod
    def _from_row(cls, r, table_or_view: Table | View):
        columns = table_or_view.column_names

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
        [embeds_view] = [v for v in cls.views if v.name == "articles_embeddings"]
        d = cls._from_row(r, embeds_view)
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
                self._from_row(a, self._view_by_name["snapshot_apparitions"])
                | {"time_diff": a[13]}
                for a in main_articles
            ]

    async def add_page(self, collection, page, dt):
        async with self.conn as conn:
            site_id = await self._add_site(conn, collection.name, collection.url)
            snapshot_id = await self._add_snapshot(conn, site_id, page.snapshot.id, dt)
            article_id = await self._add_featured_article(
                conn, page.main_article.article.original
            )
            main_article_snap_id = await self._add_featured_article_snapshot(
                conn, article_id, page.main_article.article
            )
            await self._add_main_article(conn, snapshot_id, main_article_snap_id)

            for t in page.top_articles:
                article_id = await self._add_featured_article(conn, t.article.original)
                top_article_snap_id = await self._add_featured_article_snapshot(
                    conn, article_id, t.article
                )
                await self._add_top_article(conn, snapshot_id, top_article_snap_id, t)
            await conn.commit()

            return site_id

    async def _add_site(self, conn, name: str, original_url: str) -> int:
        return await self._insert_or_get(
            conn,
            self._insert_stmt("sites", ["name", "original_url"]),
            [name, original_url],
            "SELECT id FROM sites WHERE name = ?",
            [name],
        )

    async def _add_snapshot(
        self, conn, site_id: int, snapshot: InternetArchiveSnapshotId, virtual: datetime
    ) -> int:
        return await self._insert_or_get(
            conn,
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
            "SELECT id FROM snapshots WHERE timestamp_virtual = ? AND site_id = ?",
            [virtual, site_id],
        )

    async def _add_featured_article(self, conn, article: FeaturedArticle):
        return await self._insert_or_get(
            conn,
            self._insert_stmt("featured_articles", ["url"]),
            [str(article.url)],
            "SELECT id FROM featured_articles WHERE url = ?",
            [str(article.url)],
        )

    async def _add_featured_article_snapshot(
        self, conn, featured_article_id: int, article: FeaturedArticleSnapshot
    ):
        return await self._insert_or_get(
            conn,
            self._insert_stmt(
                "featured_article_snapshots",
                ["title", "url", "featured_article_id"],
            ),
            [article.title, article.url, featured_article_id],
            "SELECT id FROM featured_article_snapshots WHERE featured_article_id = ? AND url = ?",
            [featured_article_id, article.url],
        )

    async def _add_main_article(self, conn, snapshot_id: int, article_id: int):
        await conn.execute_insert(
            self._insert_stmt(
                "main_articles", ["snapshot_id", "featured_article_snapshot_id"]
            ),
            [snapshot_id, article_id],
        )

    async def _add_top_article(
        self, conn, snapshot_id: int, article_id: int, article: TopArticle
    ):
        await conn.execute_insert(
            self._insert_stmt(
                "top_articles",
                ["snapshot_id", "featured_article_snapshot_id", "rank"],
            ),
            [snapshot_id, article_id, article.rank],
        )

    async def _insert_or_get(
        self,
        conn,
        insert_stmt: str,
        insert_args: list[Any],
        select_stmt: str,
        select_args: list[Any],
    ) -> int:
        (id_,) = await conn.execute_insert(insert_stmt, insert_args)

        if id_ == 0:
            [(id_,)] = await conn.execute_fetchall(select_stmt, select_args)

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

    @property
    def _table_by_name(self):
        return {t.name: t for t in self.tables}

    @property
    def _view_by_name(self):
        return {v.name: v for v in self.views}
