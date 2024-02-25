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


@frozen
class InternetArchiveSnapshot:
    timestamp: str
    original: str

    @property
    def url(self):
        return f"http://web.archive.org/web/{self.timestamp}/{self.original}"

    @staticmethod
    def from_record(rec: CdxRecord):
        return InternetArchiveSnapshot(timestamp=rec.timestamp, original=rec.original)


@frozen
class LeMondeTopArticle:
    title: str
    url: str

    @staticmethod
    def from_soup(soup: BeautifulSoup):
        return cattrs.structure(dict(title=soup.text.strip(), url=soup.find("a")["href"]), LeMondeTopArticle)


@frozen
class LeMondeMainPage:
    snapshot: InternetArchiveSnapshot
    soup: BeautifulSoup

    def get_top_articles(self):
        return [LeMondeTopArticle.from_soup(s) for s in self.soup.find_all("div", class_="top-article")]


class InternetArchiveClient:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

    def __init__(self):
        self.client = HttpClient()

    async def search_snapshots(self, req: CdxRequest):
        def to_snapshot(line):
            record = CdxRecord.parse_line(line)
            return InternetArchiveSnapshot.from_record(record)

        resp = await self.client.aget(
            "http://web.archive.org/cdx/search/cdx?", req.into_params()
        )

        return [to_snapshot(line) for line in resp.splitlines()]

    async def fetch_and_parse_snapshot(self, snap: InternetArchiveSnapshot):
        resp = await self.client.aget(snap.url)
        return BeautifulSoup(resp, "html.parser")


async def get_latest_snaps():
    dates = [date.today() - timedelta(days=n) for n in range(0, 10)]
    ia = InternetArchiveClient()

    def build_request(d):
        req = CdxRequest(
            url="lemonde.fr", from_=d, to_=d, limit=10, filter="statuscode:200"
        )
        return ia.search_snapshots(req)

    async def parse_snap(snap):
        soup = await ia.fetch_and_parse_snapshot(snap)
        return LeMondeMainPage(snap, soup)

    snaps = await asyncio.gather(*[build_request(d) for d in dates])
    top = await asyncio.gather(*[parse_snap(s[0]) for s in snaps])
    for t in top:
        print(t.get_top_articles()[0], t.get_top_articles()[-1])


asyncio.run(get_latest_snaps())
