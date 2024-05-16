import asyncpg
import traceback

from .connection import DbConnection


class DbConnectionPostgres(DbConnection):
    def __init__(self, conn_str):
        self.connection_string = conn_str
        self.conn = None

    async def __aenter__(self):
        self.conn = await asyncpg.connect(self.connection_string)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.conn.close()
        self.conn = None

    async def execute(self, *args, **kwargs):
        return await self.conn.execute(*args, **kwargs)

    async def execute_fetchall(self, *args, **kwargs):
        try:
            res = await self.conn.fetch(*args, **kwargs)
            return res
        except Exception as e:
            print("exception on exec of : ", args)
            traceback.print_exception(e)
            raise e

    async def execute_insert(self, *args, **kwargs):
        try:
            ret = await self.conn.execute(*args, **kwargs)
            return ret
        except Exception as e:
            print("exception on exec of : ", args)
            traceback.print_exception(e)
            raise e

    async def commit(self):
        return
