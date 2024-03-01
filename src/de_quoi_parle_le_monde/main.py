from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import InternetArchiveClient
from de_quoi_parle_le_monde.le_monde import le_monde_collection


@frozen
class ArchiveDownloader:
    client: HttpClient

    @staticmethod
    def last_n_days(n):
        return [
            datetime.combine(date.today() - timedelta(days=i), time(hour=18))
            for i in range(0, n)
        ]

    async def get_latest_snaps(self, collection, dts):
        async with self.client.session() as session:
            ia = InternetArchiveClient(session)

            async def handle_snap(collection, dt):
                id_closest = await ia.get_snapshot_id_closest_to(collection.url, dt)
                closest = await ia.fetch(id_closest)
                return await collection.MainPageClass.from_snapshot(closest)

            return await asyncio.gather(*[handle_snap(collection, d) for d in dts])


http_client = HttpClient()
dler = ArchiveDownloader(http_client)
snaps = asyncio.run(
    dler.get_latest_snaps(le_monde_collection, ArchiveDownloader.last_n_days(1))
)

for s in snaps:
    print(s.snapshot.id.timestamp, s.top_articles[0], s.main_article)
