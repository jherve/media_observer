from attrs import frozen, field
from typing import Optional, ClassVar, NewType
from datetime import date, datetime, timedelta
import cattrs

from de_quoi_parle_le_monde.http import HttpSession

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


class SnapshotNotYetAvailable(Exception):
    timestamp: datetime


@frozen
class InternetArchiveSnapshotId:
    timestamp: Timestamp
    original: str

    @property
    def url(self):
        return f"http://web.archive.org/web/{timestamp_to_str(self.timestamp)}/{self.original}"

    @staticmethod
    def from_record(rec: CdxRecord):
        return InternetArchiveSnapshotId(timestamp=rec.timestamp, original=rec.original)


@frozen
class InternetArchiveSnapshot:
    id: InternetArchiveSnapshotId
    text: str = field(repr=False)


@frozen
class InternetArchiveClient:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    session: HttpSession
    search_url: ClassVar[str] = "http://web.archive.org/cdx/search/cdx"

    async def search_snapshots(
        self, req: CdxRequest
    ) -> list[InternetArchiveSnapshotId]:
        def to_snapshot_id(line):
            record = CdxRecord.parse_line(line)
            return InternetArchiveSnapshotId.from_record(record)

        resp = await self.session.get(self.search_url, req.into_params())

        return [to_snapshot_id(line) for line in resp.splitlines()]

    async def fetch(self, id_: InternetArchiveSnapshotId) -> str:
        resp = await self.session.get(id_.url)
        return InternetArchiveSnapshot(id_, resp)

    async def get_snapshot_id_closest_to(self, url, dt):
        req = CdxRequest(
            url=url,
            from_=dt - timedelta(hours=6.0),
            # It does not make sense to ask for snapshots in the future.
            # In the case where the requested `dt` is in the future, this
            # also allows to always send a new actual request and not
            # hit the cache, but this is obviously an implementation detail
            # of the HTTP layer that this client should not be aware of..
            to_=min(dt + timedelta(hours=6.0), datetime.now()),
            filter="statuscode:200",
            # Just to be safe, add an arbitrary limit to the number of values returned
            limit=100,
        )

        all_snaps = await self.search_snapshots(req)
        if all_snaps:
            return min(all_snaps, key=lambda s: abs(s.timestamp - dt))
        else:
            raise SnapshotNotYetAvailable(dt)
