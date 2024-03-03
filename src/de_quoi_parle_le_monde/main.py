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

    @staticmethod
    async def handle_snap(ia, collection, storage, dt):
        id_closest = await ia.get_snapshot_id_closest_to(collection.url, dt)
        closest = await ia.fetch(id_closest)

        try:
            main_page = await collection.MainPageClass.from_snapshot(closest)
        except AttributeError as e:
            print(f"error while processing {id_closest}")
            raise e

        site_id = await storage.add_site(collection.url)
        snapshot_id = await storage.add_snapshot(site_id, main_page.snapshot.id, dt)
        await storage.add_main_article(snapshot_id, main_page.main_article)
        for t in main_page.top_articles:
            await storage.add_top_article(snapshot_id, t)


async def main(dler: ArchiveDownloader):
    storage = await Storage.create()
    dts = ArchiveDownloader.last_n_days(20)

    async with dler.client.session() as session:
        ia = InternetArchiveClient(session)

        return await asyncio.gather(
            *[
                ArchiveDownloader.handle_snap(ia, c, storage, d)
                for d in dts
                for c in media_collection.values()
            ]
        )


http_client = HttpClient()
dler = ArchiveDownloader(http_client)

asyncio.run(main(dler))
