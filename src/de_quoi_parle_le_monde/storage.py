import aiosqlite

from de_quoi_parle_le_monde.article import MainArticle, TopArticle


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
                CREATE TABLE IF NOT EXISTS main_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    site TEXT,
                    title TEXT,
                    url TEXT
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS main_articles_unique_idx_timestamp_site
                ON main_articles (timestamp, site);
            """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS top_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    site TEXT,
                    title TEXT,
                    url TEXT,
                    rank INTEGER
                );
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS top_articles_unique_idx_timestamp_site_rank
                ON top_articles (timestamp, site, rank);
                """
            )

    async def add_main_article(self, timestamp: str, site: str, article: MainArticle):
        async with aiosqlite.connect(self.conn_str) as conn:
            await conn.execute_insert(
                """
                INSERT INTO main_articles (timestamp, site, title, url)
                VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING;
                """,
                [timestamp, site, article.title, article.url],
            )
            await conn.commit()

    async def add_top_article(self, timestamp: str, site: str, article: TopArticle):
        async with aiosqlite.connect(self.conn_str) as conn:
            await conn.execute_insert(
                """
                INSERT INTO top_articles (timestamp, site, title, url, rank)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING;
                """,
                [timestamp, site, article.title, article.url, article.rank],
            )
            await conn.commit()
