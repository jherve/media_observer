from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import InternetArchiveClient
from de_quoi_parle_le_monde.medias import media_collection
from de_quoi_parle_le_monde.storage import Storage


@frozen
class ArchiveDownloader:
    client: HttpClient

    @staticmethod
    def last_n_days(n):
        return [
            datetime.combine(date.today() - timedelta(days=i), time(hour=18))
            for i in range(1, n)
        ]

    async def get_latest_snaps(self, collection, dts, storage):
        async with self.client.session() as session:
            ia = InternetArchiveClient(session)

            async def handle_snap(collection, storage, dt):
                id_closest = await ia.get_snapshot_id_closest_to(collection.url, dt)
                closest = await ia.fetch(id_closest)
                try:
                    main_page = await collection.MainPageClass.from_snapshot(closest)
                except AttributeError as e:
                    print(f"error while processing {id_closest}")
                    raise e
                await storage.add_snapshot(main_page.snapshot.id)
                await storage.add_main_article(
                    main_page.snapshot.id.timestamp,
                    main_page.snapshot.id.original,
                    main_page.main_article,
                )
                for t in main_page.top_articles:
                    await storage.add_top_article(
                        main_page.snapshot.id.timestamp,
                        main_page.snapshot.id.original,
                        t,
                    )

            return await asyncio.gather(
                *[handle_snap(collection, storage, d) for d in dts]
            )


async def main(dler):
    storage = await Storage.create()
    for c in media_collection.values():
        await dler.get_latest_snaps(c, ArchiveDownloader.last_n_days(20), storage)


http_client = HttpClient()
dler = ArchiveDownloader(http_client)

asyncio.run(main(dler))
