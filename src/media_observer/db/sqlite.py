import asyncio
import aiosqlite


class SqliteConnection:
    def __init__(self, conn_str):
        self.connection_string = conn_str
        self.semaphore = asyncio.Semaphore(1)

    async def __aenter__(self):
        await self.semaphore.acquire()
        self.conn = await aiosqlite.connect(self.connection_string)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Reproduce asyncpg' behaviour where commit is implicit
        await self.conn.commit()
        await self.conn.close()
        self.conn = None
        self.semaphore.release()

    async def execute(self, *args, **kwargs):
        return await self.conn.execute(*args, **kwargs)

    async def execute_fetchall(self, *args, **kwargs):
        return await self.conn.execute_fetchall(*args, **kwargs)

    async def execute_insert(self, *args, **kwargs):
        return await self.conn.execute_insert(*args, **kwargs)

    def transaction(self):
        class DummyTransaction:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return

        return DummyTransaction()


class SqliteBackend:
    def __init__(self, conn_path):
        self.conn_path = conn_path

    def get_connection(self):
        return SqliteConnection(self.conn_path)

    @staticmethod
    async def create(conn_path):
        return SqliteBackend(conn_path)

    async def close(self): ...
