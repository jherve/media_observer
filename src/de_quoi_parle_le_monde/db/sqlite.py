import asyncio
import aiosqlite

from .connection import DbConnection


class DbConnectionSQLite(DbConnection):
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
