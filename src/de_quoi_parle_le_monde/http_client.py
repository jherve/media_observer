import requests_cache
from aiohttp_client_cache import CachedSession, SQLiteBackend


class HttpClient:
    def __init__(self):
        self.http_session = requests_cache.CachedSession("ia", backend="sqlite")
        self.cache = SQLiteBackend("http")

    def get(self, url, params=None):
        return self.http_session.get(url, params)

    async def aget(self, url, params=None):
        async with CachedSession(cache=SQLiteBackend("http")) as session:
            async with session.get(url, allow_redirects=True, params=params) as resp:
                return await resp.text()
