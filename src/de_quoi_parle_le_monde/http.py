from aiohttp_client_cache import CachedSession, SQLiteBackend


class HttpClient:
    async def aget(self, url, params=None):
        async with CachedSession(cache=SQLiteBackend("http")) as session:
            async with session.get(url, allow_redirects=True, params=params) as resp:
                return await resp.text()
