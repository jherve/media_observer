from attrs import define
from aiohttp_client_cache import SQLiteBackend
from aiohttp_client_cache.session import CacheMixin
from aiohttp.client import ClientSession
from aiolimiter import AsyncLimiter
import asyncio


class SemaphoreMixin:
    async def _request(self, *args, **kwargs):
        await self.sem.acquire()
        req = await super()._request(*args, **kwargs)
        self.sem.release()
        return req


class RateLimiterMixin:
    async def _request(self, *args, **kwargs):
        await self.limiter.acquire()
        return await super()._request(*args, **kwargs)


@define
class LimitedCachedSession(CacheMixin, SemaphoreMixin, RateLimiterMixin, ClientSession):
    sem: asyncio.Semaphore
    limiter: AsyncLimiter
    cache: SQLiteBackend

    def __init__(self):
        self.sem = asyncio.Semaphore(5)
        self.limiter = AsyncLimiter(2.0, 1.0)
        super().__init__(cache=SQLiteBackend("http"))


class HttpSession:
    def __init__(self):
        self.session = LimitedCachedSession()

    async def get(self, url, params=None):
        async with self.session.get(url, allow_redirects=True, params=params) as resp:
            return await resp.text()

    async def __aenter__(self):
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return await self.session.__aexit__(exc_type, exc, tb)


class HttpClient:
    def session(self):
        return HttpSession()
