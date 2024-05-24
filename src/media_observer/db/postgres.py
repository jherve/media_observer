import asyncpg


class PostgresConnection:
    def __init__(self, coro):
        self.coro = coro

    async def __aenter__(self):
        self.conn = await self.coro.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.coro.__aexit__(exc_type, exc, tb)

    async def execute(self, *args, **kwargs):
        return await self.conn.execute(*args, **kwargs)

    async def execute_insert(self, *args, **kwargs):
        return await self.conn.execute(*args, **kwargs)

    async def execute_fetchall(self, *args, **kwargs):
        return await self.conn.fetch(*args, **kwargs)

    def transaction(self):
        return self.conn.transaction()


class PostgresBackend:
    def __init__(self, pool):
        self.pool = pool

    def get_connection(self):
        return PostgresConnection(self.pool.acquire())

    @staticmethod
    async def create(conn_url):
        pool = await asyncpg.create_pool(conn_url)
        return PostgresBackend(pool)

    async def close(self):
        await self.pool.close()
