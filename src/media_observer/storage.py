from typing import Any
from datetime import datetime
import numpy as np
from yarl import URL

from config import settings
from media_observer.article import (
    ArchiveCollection,
    FrontPage,
    Article,
)
from media_observer.storage_abstraction import (
    Table,
    Reference,
    Column,
    UniqueIndex,
    View,
    StorageAbc,
)
from media_observer.db.sqlite import SqliteBackend
from media_observer.db.postgres import PostgresBackend
from media_observer.internet_archive import InternetArchiveSnapshotId


table_sites = Table(
    name="sites",
    columns=[
        Column(name="id", primary_key=True),
        Column(name="name", type_="TEXT"),
        Column(name="original_url", type_="TEXT"),
    ],
)
table_frontpages = Table(
    name="frontpages",
    columns=[
        Column(name="id", primary_key=True),
        Column(
            name="site_id",
            references=Reference("sites", "id", on_delete="cascade"),
        ),
        Column(name="timestamp", type_="timestamp with time zone"),
        Column(name="timestamp_virtual", type_="timestamp with time zone"),
        Column(name="url_original", type_="TEXT"),
        Column(name="url_snapshot", type_="TEXT"),
    ],
)
table_articles = Table(
    name="articles",
    columns=[
        Column(name="id", primary_key=True),
        Column(name="url", type_="TEXT"),
    ],
)
table_titles = Table(
    name="titles",
    columns=[
        Column(name="id", primary_key=True),
        Column(name="text", type_="TEXT"),
    ],
)
table_main_articles = Table(
    name="main_articles",
    columns=[
        Column(name="id", primary_key=True),
        Column(name="url", type_="TEXT"),
        Column(
            name="frontpage_id",
            references=Reference("frontpages", "id", on_delete="cascade"),
        ),
        Column(
            name="article_id",
            references=Reference("articles", "id", on_delete="cascade"),
        ),
        Column(
            name="title_id",
            references=Reference("titles", "id", on_delete="cascade"),
        ),
    ],
)
table_top_articles = Table(
    name="top_articles",
    columns=[
        Column(name="id", primary_key=True),
        Column(name="url", type_="TEXT"),
        Column(name="rank", type_="INTEGER"),
        Column(
            name="frontpage_id",
            references=Reference("frontpages", "id", on_delete="cascade"),
        ),
        Column(
            name="article_id",
            references=Reference("articles", "id", on_delete="cascade"),
        ),
        Column(
            name="title_id",
            references=Reference("titles", "id", on_delete="cascade"),
        ),
    ],
)
table_embeddings = Table(
    name="embeddings",
    columns=[
        Column(name="id", primary_key=True),
        Column(
            name="title_id", references=Reference("titles", "id", on_delete="cascade")
        ),
        Column(name="vector", type_="bytea"),
    ],
)
view_frontpages = View(
    name="frontpages_view",
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
            fp.id,
            si.id AS site_id,
            si.name AS site_name,
            si.original_url AS site_original_url,
            fp.timestamp,
            fp.timestamp_virtual
        FROM
            frontpages AS fp
        JOIN
            sites AS si ON si.id = fp.site_id
        """,
)
view_articles = View(
    name="articles_view",
    column_names=[
        "id",
        "title",
        "title_id",
        "url_archive",
        "url_article",
        "main_in_frontpage_id",
        "top_in_frontpage_id",
        "rank",
    ],
    create_stmt="""
        SELECT
            a.id,
            t.text AS title,
            t.id AS title_id,
            ma.url AS url_archive,
            a.url AS url_article,
            ma.frontpage_id AS main_in_frontpage_id,
            NULL AS top_in_frontpage_id,
            NULL AS rank
        FROM articles a
        JOIN main_articles ma ON ma.article_id = a.id
        JOIN titles t ON t.id = ma.title_id

        UNION ALL

        SELECT
            a.id,
            t.text AS title,
            t.id AS title_id,
            ta.url AS url_archive,
            a.url AS url_article,
            NULL AS main_in_frontpage_id,
            ta.frontpage_id AS top_in_frontpage_id,
            ta.rank
        FROM articles a
        JOIN top_articles ta ON ta.article_id = a.id
        JOIN titles t ON t.id = ta.title_id
        """,
)
view_articles_on_frontpage = View(
    name="articles_on_frontpage_view",
    column_names=[
        "frontpage_id",
        "site_id",
        "site_name",
        "site_original_url",
        "timestamp",
        "timestamp_virtual",
        "article_id",
        "title",
        "title_id",
        "url_archive",
        "url_article",
        "is_main",
        "rank",
    ],
    create_stmt="""
        SELECT
            fpv.id AS frontpage_id,
            fpv.site_id,
            fpv.site_name,
            fpv.site_original_url,
            fpv."timestamp",
            fpv.timestamp_virtual,
            av.id AS article_id,
            av.title,
            av.title_id,
            av.url_archive,
            av.url_article,
            av.main_in_frontpage_id IS NOT NULL AS is_main,
            av.rank
        FROM articles_view av
        JOIN frontpages_view fpv ON fpv.id = av.main_in_frontpage_id OR fpv.id = av.top_in_frontpage_id
    """,
)


class Storage(StorageAbc):
    tables = [
        table_sites,
        table_frontpages,
        table_articles,
        table_titles,
        table_main_articles,
        table_top_articles,
        table_embeddings,
    ]

    views = [
        view_frontpages,
        view_articles,
        view_articles_on_frontpage,
    ]

    indexes = [
        UniqueIndex(table="sites", columns=["name"]),
        UniqueIndex(table="frontpages", columns=["timestamp_virtual", "site_id"]),
        UniqueIndex(table="articles", columns=["url"]),
        UniqueIndex(table="titles", columns=["text"]),
        UniqueIndex(table="main_articles", columns=["frontpage_id", "article_id"]),
        UniqueIndex(
            table="top_articles", columns=["frontpage_id", "article_id", "rank"]
        ),
        UniqueIndex(table="embeddings", columns=["title_id"]),
    ]

    def __init__(self, backend):
        self.backend = backend

    async def close(self):
        await self.backend.close()

    @staticmethod
    async def create():
        # We try to reproduce the scheme used by SQLAlchemy for Database-URLs
        # https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
        conn_url = URL(settings.database_url)
        backend = None

        if conn_url.scheme == "sqlite":
            if conn_url.path.startswith("//"):
                raise ValueError("Absolute URLs not supported for sqlite")
            elif conn_url.path.startswith("/"):
                backend = await SqliteBackend.create(conn_url.path[1:])
        elif conn_url.scheme == "postgresql":
            backend = await PostgresBackend.create(settings.database_url)
        else:
            raise ValueError("Only the SQLite backend is supported")

        storage = Storage(backend)
        await storage._create_db()
        return storage

    async def _create_db(self):
        async with self.backend.get_connection() as conn:
            for t in self.tables:
                await t.create_if_not_exists(conn)

            for i in self.indexes:
                await i.create_if_not_exists(conn)

            for v in self.views:
                await v.create_if_not_exists(conn)

    async def exists_frontpage(self, name: str, dt: datetime):
        async with self.backend.get_connection() as conn:
            exists = await conn.execute_fetchall(
                """
                    SELECT 1
                    FROM frontpages f
                    JOIN sites s ON s.id = f.site_id
                    WHERE s.name = $1 AND timestamp_virtual = $2
                """,
                name,
                dt,
            )

        return exists != []

    @classmethod
    def _from_row(cls, r, table_or_view: Table | View):
        columns = table_or_view.column_names

        return {col: r[idx] for idx, col in enumerate(columns)}

    async def list_neighbouring_main_articles(
        self,
        site_id: int,
        timestamp: datetime | None = None,
    ):
        async with self.backend.get_connection() as conn:
            if timestamp is None:
                [row] = await conn.execute_fetchall(
                    """
                    SELECT timestamp_virtual
                    FROM frontpages_view
                    WHERE site_id = $1
                    ORDER BY timestamp_virtual DESC
                    LIMIT 1
                    """,
                    site_id,
                )
                timestamp = row["timestamp_virtual"]

            # This query is the union of 3 queries that respectively fetch :
            #   * articles published at the same time as the queried article (including the queried article)
            #   * the article published just after, on the same site
            #   *the article published just before, on the same site
            main_articles = await conn.execute_fetchall(
                """
                WITH aof_diff AS (
                    SELECT aof.*, EXTRACT(EPOCH FROM aof.timestamp_virtual - $2) :: integer AS time_diff
                    FROM articles_on_frontpage_view aof
                )
                SELECT * FROM (
                    SELECT * FROM aof_diff
                    WHERE is_main AND time_diff = 0
                )
                UNION ALL
                SELECT * FROM (
                    SELECT * FROM aof_diff
                    WHERE is_main AND site_id = $1 AND time_diff > 0
                    ORDER BY time_diff
                    LIMIT 1
                )
                UNION ALL
                SELECT * FROM (
                    SELECT * FROM aof_diff
                    WHERE is_main AND site_id = $1 AND time_diff < 0
                    ORDER BY time_diff DESC
                    LIMIT 1
                )
                """,
                site_id,
                timestamp,
            )

            return [
                self._from_row(a, self._view_by_name["articles_on_frontpage_view"])
                | {"time_diff": a[13]}
                for a in main_articles
            ]

    async def list_all_titles_without_embedding(self):
        async with self.backend.get_connection() as conn:
            rows = await conn.execute_fetchall("""
                SELECT t.*
                FROM public.titles AS t
                WHERE NOT EXISTS (SELECT 1 FROM embeddings WHERE title_id = t.id)
            """)

            return [self._from_row(r, self._table_by_name["titles"]) for r in rows]

    async def list_all_embeddings(self):
        async with self.backend.get_connection() as conn:
            rows = await conn.execute_fetchall(
                """
                    SELECT *
                    FROM embeddings
                """,
            )

            return [self._from_embeddings_row(r) for r in rows]

    async def list_articles_on_frontpage(self, title_ids: list[int]):
        if len(title_ids) == 0:
            return []

        async with self.backend.get_connection() as conn:
            rows = await conn.execute_fetchall(
                f"""
                    SELECT *
                    FROM articles_on_frontpage_view
                    WHERE title_id IN ({self._placeholders(*title_ids)})
                """,
                *title_ids,
            )

            return [
                self._from_row(r, self._view_by_name["articles_on_frontpage_view"])
                for r in rows
            ]

    @classmethod
    def _from_embeddings_row(cls, r):
        [embeds_table] = [t for t in cls.tables if t.name == "embeddings"]
        d = cls._from_row(r, embeds_table)
        d.update(vector=np.frombuffer(d["vector"], dtype="float32"))

        return d

    async def add_embedding(self, title_id: int, embedding):
        async with self.backend.get_connection() as conn:
            await conn.execute_insert(
                self._insert_stmt(
                    "embeddings",
                    ["title_id", "vector"],
                ),
                title_id,
                embedding,
            )

    async def list_sites(self):
        async with self.backend.get_connection() as conn:
            sites = await conn.execute_fetchall("SELECT * FROM sites")
            return [self._from_row(s, self._table_by_name["sites"]) for s in sites]

    async def add_page(
        self, collection: ArchiveCollection, page: FrontPage, dt: datetime
    ):
        assert dt.tzinfo is not None

        async with self.backend.get_connection() as conn:
            async with conn.transaction():
                site_id = await self._add_site(conn, collection.name, collection.url)
                frontpage_id = await self._add_frontpage(
                    conn, site_id, page.snapshot.id, dt
                )
                article_id = await self._add_article(
                    conn, page.main_article.article.original
                )
                title_id = await self._add_title(conn, page.main_article.article.title)
                await self._add_main_article(
                    conn,
                    frontpage_id,
                    article_id,
                    title_id,
                    page.main_article.article.url,
                )

                for t in page.top_articles:
                    article_id = await self._add_article(conn, t.article.original)
                    title_id = await self._add_title(conn, t.article.title)
                    await self._add_top_article(
                        conn, frontpage_id, article_id, title_id, t.article.url, t.rank
                    )

        return site_id

    async def _add_site(self, conn, name: str, original_url: str) -> int:
        return await self._insert_or_get(
            conn,
            self._insert_stmt("sites", ["name", "original_url"]),
            [name, original_url],
            "SELECT id FROM sites WHERE name = $1",
            [name],
        )

    async def _add_frontpage(
        self, conn, site_id: int, snapshot: InternetArchiveSnapshotId, virtual: datetime
    ) -> int:
        return await self._insert_or_get(
            conn,
            self._insert_stmt(
                "frontpages",
                [
                    "timestamp",
                    "site_id",
                    "timestamp_virtual",
                    "url_original",
                    "url_snapshot",
                ],
            ),
            [snapshot.timestamp, site_id, virtual, snapshot.original, snapshot.url],
            "SELECT id FROM frontpages WHERE timestamp_virtual = $1 AND site_id = $2",
            [virtual, site_id],
        )

    async def _add_article(self, conn, article: Article):
        return await self._insert_or_get(
            conn,
            self._insert_stmt("articles", ["url"]),
            [str(article.url)],
            "SELECT id FROM articles WHERE url = $1",
            [str(article.url)],
        )

    async def _add_title(self, conn, title: str):
        return await self._insert_or_get(
            conn,
            self._insert_stmt("titles", ["text"]),
            [title],
            "SELECT id FROM titles WHERE text = $1",
            [title],
        )

    async def _add_main_article(
        self, conn, frontpage_id: int, article_id: int, title_id: int, url: URL
    ):
        await conn.execute_insert(
            self._insert_stmt(
                "main_articles", ["frontpage_id", "article_id", "title_id", "url"]
            ),
            frontpage_id,
            article_id,
            title_id,
            str(url),
        )

    async def _add_top_article(
        self,
        conn,
        frontpage_id: int,
        article_id: int,
        title_id: int,
        url: URL,
        rank: int,
    ):
        await conn.execute_insert(
            self._insert_stmt(
                "top_articles",
                ["frontpage_id", "article_id", "title_id", "url", "rank"],
            ),
            frontpage_id,
            article_id,
            title_id,
            str(url),
            rank,
        )

    async def _insert_or_get(
        self,
        conn,
        insert_stmt: str,
        insert_args: list[Any],
        select_stmt: str,
        select_args: list[Any],
    ) -> int:
        await conn.execute_insert(insert_stmt, *insert_args)

        [(id_,)] = await conn.execute_fetchall(select_stmt, *select_args)

        return id_

    @staticmethod
    def _insert_stmt(table, cols):
        cols_str = ", ".join(cols)
        return f"""
            INSERT INTO {table} ({cols_str})
            VALUES ({Storage._placeholders(*cols)})
            ON CONFLICT DO NOTHING
        """

    @staticmethod
    def _placeholders(*args):
        return ", ".join([f"${idx + 1}" for idx, _ in enumerate(args)])

    @property
    def _table_by_name(self):
        return {t.name: t for t in self.tables}

    @property
    def _view_by_name(self):
        return {v.name: v for v in self.views}
