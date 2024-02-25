import requests
import requests_cache
from attrs import frozen
from typing import Optional, ClassVar
from datetime import date, datetime
import cattrs
from requests_cache.models.response import CachedResponse
from requests_cache.backends.sqlite import SQLiteCache
from bs4 import BeautifulSoup

http_session = requests_cache.CachedSession("ia",backend="sqlite")


@frozen
class CdxRecord:
    urlkey: str
    timestamp: int
    original: str
    mimetype: str
    statuscode: int
    digest: str
    length:int

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
        return {self._translate_key(k): self._stringify_value(v) for k, v in cattrs.unstructure(self).items()}

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


class InternetArchive:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

    @staticmethod
    def search_snapshots(req: CdxRequest):
        resp = http_session.get("http://web.archive.org/cdx/search/cdx?", req.into_params())
        return [CdxRecord.parse_line(l) for l in resp.text.splitlines()]

    @staticmethod
    def get_snapshot(url, snap_date):
        return http_session.get(f"http://web.archive.org/web/{snap_date}/{url}")


class WebPage:
    def __init__(self, doc):
        self.soup = BeautifulSoup(doc, 'html.parser')

    def get_top_articles_titles(self):
        return [s.text.strip() for s in self.soup.find_all("div", class_="top-article")]

def get_latest_snap():
    req = CdxRequest(url="lemonde.fr", from_=date.today(), to_=date.today(), limit=10, filter="statuscode:200")
    results = InternetArchive.search_snapshots(req)

    latest = results[-1]
    print(latest)
    return InternetArchive.get_snapshot(latest.original, latest.timestamp)


print(WebPage(get_latest_snap().text).get_top_articles_titles())
