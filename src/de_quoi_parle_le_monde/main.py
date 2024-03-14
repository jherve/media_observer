from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import (
    InternetArchiveClient,
    SnapshotNotYetAvailable,
)
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
        try:
            id_closest = await ia.get_snapshot_id_closest_to(collection.url, dt)
        except SnapshotNotYetAvailable as e:
            print(f"Snapshot for {collection.url} @ {dt} not yet available")
            raise e

        closest = await ia.fetch(id_closest)

        try:
            main_page = await collection.MainPageClass.from_snapshot(closest)
        except AttributeError as e:
            print(f"error while processing {id_closest}")
            raise e

        site_id = await storage.add_site(collection.url)
        snapshot_id = await storage.add_snapshot(site_id, main_page.snapshot.id, dt)

        main_id = await storage.add_featured_article_snapshot(main_page.main_article.article)
        await storage.add_main_article(snapshot_id, main_id)

        for t in main_page.top_articles:
            article_id = await storage.add_featured_article_snapshot(t.article)
            await storage.add_top_article(snapshot_id, article_id, t)


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
            ],
            return_exceptions=True,
        )


http_client = HttpClient()
dler = ArchiveDownloader(http_client)

asyncio.run(main(dler))
