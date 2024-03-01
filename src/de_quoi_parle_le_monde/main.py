from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import InternetArchiveClient
from de_quoi_parle_le_monde.le_monde import LeMondeArchive, LeMondeMainPage


@frozen
class ArchiveDownloader:
    client: HttpClient

    @staticmethod
    def last_n_days(n):
        return [
            datetime.combine(date.today() - timedelta(days=i), time(hour=18))
            for i in range(0, n)
        ]

    async def get_latest_snaps(self, dts):
        async with self.client.session() as session:
            ia = InternetArchiveClient(session)

            async def handle_snap(dt):
                closest = await ia.get_snapshot_closest_to(LeMondeArchive.url, dt)
                closest_body = await ia.fetch(closest)
                return await LeMondeMainPage.from_content(closest, closest_body)

            return await asyncio.gather(*[handle_snap(d) for d in dts])


http_client = HttpClient()
dler = ArchiveDownloader(http_client)
snaps = asyncio.run(dler.get_latest_snaps(ArchiveDownloader.last_n_days(5)))

for s in snaps:
    print(s.snapshot.timestamp, s.get_top_articles()[0], s.main_article())
