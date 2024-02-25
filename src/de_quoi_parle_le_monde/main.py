import requests_cache
from attrs import frozen
from typing import Optional, ClassVar
from datetime import date, datetime, timedelta
import cattrs
from bs4 import BeautifulSoup
from aiohttp_client_cache import CachedSession, SQLiteBackend
import asyncio


@frozen
class CdxRecord:
    urlkey: str
    timestamp: int
    original: str
    mimetype: str
    statuscode: int
    digest: str
    length: int

    @staticmethod
    def parse_line(line: str):
        return cattrs.structure_attrs_fromtuple(line.split(" "), CdxRecord)


@frozen
class CdxRequest:
    url: str
    filter: Optional[str] = None
    from_: Optional[date | datetime] = None
    to_: Optional[date | datetime] = None
    limit: Optional[int] = None

    translation_dict: ClassVar[dict] = dict(from_="from", to_="to")
    date_format: ClassVar[str] = "%Y%m%d"
    datetime_format: ClassVar[str] = "%Y%m%d%H%M%S"

    def into_params(self) -> dict[str, str]:
        return {
            self._translate_key(k): self._stringify_value(v)
            for k, v in cattrs.unstructure(self).items()
        }

    @classmethod
    def _translate_key(cls, key: str) -> str:
        return cls.translation_dict.get(key, key)

    @classmethod
    def _stringify_value(cls, v) -> str:
        if isinstance(v, date):
            return v.strftime(cls.date_format)
        elif isinstance(v, datetime):
            return v.strftime(cls.datetime_format)
        else:
            return str(v)


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


class InternetArchiveClient:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

    def __init__(self):
        self.client = HttpClient()

    async def search_snapshots(self, req: CdxRequest):
        resp = await self.client.aget(
            "http://web.archive.org/cdx/search/cdx?", req.into_params()
        )
        return [CdxRecord.parse_line(line) for line in resp.splitlines()]

    async def get_snapshot(self, url, snap_date):
        return await self.client.aget(f"http://web.archive.org/web/{snap_date}/{url}")


class WebPage:
    def __init__(self, doc):
        self.soup = BeautifulSoup(doc, "html.parser")

    def get_top_articles_titles(self):
        return [s.text.strip() for s in self.soup.find_all("div", class_="top-article")]


async def get_latest_snaps():
    dates = [date.today() - timedelta(days=n) for n in range(0, 10)]
    ia = InternetArchiveClient()

    def build_request(d):
        req = CdxRequest(
            url="lemonde.fr", from_=d, to_=d, limit=10, filter="statuscode:200"
        )
        return ia.search_snapshots(req)

    async def get_snap(res):
        snap = await ia.get_snapshot(res[-1].original, res[-1].timestamp)
        page = WebPage(snap)
        return page.get_top_articles_titles()

    results = await asyncio.gather(*[build_request(d) for d in dates])
    top = await asyncio.gather(*[get_snap(r) for r in results])
    for t in top:
        print(t[0], t[-1])


asyncio.run(get_latest_snaps())
