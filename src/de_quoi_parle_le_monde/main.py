from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import InternetArchiveClient
from de_quoi_parle_le_monde.le_monde import LeMondeArchive, LeMondeMainPage


async def get_latest_snaps(dts):
    http_client = HttpClient()

    async with http_client.session() as session:
        ia = InternetArchiveClient(session)

        async def req_and_parse_first_snap(dt):
            closest = await ia.get_snapshot_closest_to(LeMondeArchive.url, dt)
            closest_content = await ia.fetch_and_parse_snapshot(closest)
            return LeMondeMainPage(closest, closest_content)

        return await asyncio.gather(*[req_and_parse_first_snap(d) for d in dts])


@frozen
class ArchiveDownloader:
    client: InternetArchiveClient

    @staticmethod
    def from_http_client(http_client):
        return ArchiveDownloader(InternetArchiveClient(http_client))


dts = [
    datetime.combine(date.today() - timedelta(days=n), time(hour=18))
    for n in range(0, 5)
]
snaps = asyncio.run(get_latest_snaps(dts))
for s in snaps:
    print(s.snapshot.timestamp, s.get_top_articles()[0], s.main_article())
