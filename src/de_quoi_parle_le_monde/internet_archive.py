from attrs import frozen
from typing import Optional, ClassVar
from datetime import date, datetime
import cattrs
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.http import HttpClient


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
