from attrs import frozen
from typing import Optional, ClassVar, NewType
from datetime import date, datetime
import cattrs
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.http import HttpClient

Timestamp = NewType("Timestamp", datetime)
datetime_format = "%Y%m%d%H%M%S"


def parse_timestamp(s: str) -> Timestamp:
    return datetime.strptime(s, datetime_format)


def timestamp_to_str(ts: Timestamp) -> str:
    return ts.strftime(datetime_format)


cattrs.register_structure_hook(Timestamp, lambda v, _: parse_timestamp(v))


@frozen
class CdxRecord:
    urlkey: str
    timestamp: Timestamp
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
        # The test against datetime has to come first because `datetime` instances
        # are also `date` instances
        if isinstance(v, datetime):
            return v.strftime(cls.datetime_format)
        elif isinstance(v, date):
            return v.strftime(cls.date_format)
        else:
            return str(v)


@frozen
class InternetArchiveSnapshot:
    timestamp: Timestamp
    original: str

    @property
    def url(self):
        return f"http://web.archive.org/web/{timestamp_to_str(self.timestamp)}/{self.original}"

    @staticmethod
    def from_record(rec: CdxRecord):
        return InternetArchiveSnapshot(timestamp=rec.timestamp, original=rec.original)


@frozen
class InternetArchiveClient:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    client: HttpClient
    search_url: ClassVar[str] = "http://web.archive.org/cdx/search/cdx"

    async def search_snapshots(self, req: CdxRequest) -> list[InternetArchiveSnapshot]:
        def to_snapshot(line):
            record = CdxRecord.parse_line(line)
            return InternetArchiveSnapshot.from_record(record)

        resp = await self.client.aget(self.search_url, req.into_params())

        return [to_snapshot(line) for line in resp.splitlines()]

    async def fetch_and_parse_snapshot(
        self, snap: InternetArchiveSnapshot
    ) -> BeautifulSoup:
        resp = await self.client.aget(snap.url)
        return BeautifulSoup(resp, "lxml")
