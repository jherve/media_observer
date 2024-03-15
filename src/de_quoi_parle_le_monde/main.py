from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen
import traceback

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import (
    InternetArchiveClient,
    SnapshotNotYetAvailable,
)
from de_quoi_parle_le_monde.medias import media_collection
from de_quoi_parle_le_monde.storage import Storage


@frozen
class ArchiveDownloader:
    storage: Storage
    ia_client: InternetArchiveClient

    @staticmethod
    def last_n_days_at_hours(n: int, hours: list[int]) -> list[datetime]:
        return [
            datetime.combine(date.today() - timedelta(days=i), time(hour=h))
            for i in range(0, n)
            for h in hours
        ]

    async def find(self, collection, dt):
        return await self.ia_client.get_snapshot_id_closest_to(collection.url, dt)

    async def parse(self, collection, snapshot):
        return await collection.MainPageClass.from_snapshot(snapshot)

    async def store(self, page, collection, dt):
        site_id = await self.storage.add_site(collection.url)
        snapshot_id = await self.storage.add_snapshot(site_id, page.snapshot.id, dt)

        article_id = await self.storage.add_featured_article(
            page.main_article.article.original
        )
        main_article_snap_id = await self.storage.add_featured_article_snapshot(
            article_id, page.main_article.article
        )
        await self.storage.add_main_article(snapshot_id, main_article_snap_id)

        for t in page.top_articles:
            article_id = await self.storage.add_featured_article(t.article.original)
            top_article_snap_id = await self.storage.add_featured_article_snapshot(
                article_id, t.article
            )
            await self.storage.add_top_article(snapshot_id, top_article_snap_id, t)

    async def handle_snap(self, collection, dt):
        try:
            id_closest = await self.find(collection, dt)
        except SnapshotNotYetAvailable as e:
            print(f"Snapshot for {collection.url} @ {dt} not yet available")
            return
        except Exception as e:
            print(f"Error while trying to find snapshot for {collection.url} @ {dt}")
            traceback.print_exception(e)
            return

        try:
            closest = await self.ia_client.fetch(id_closest)
        except Exception as e:
            print(f"Error while fetching {id_closest} from {collection} @ {dt}")
            traceback.print_exception(e)
            return

        try:
            main_page = await self.parse(collection, closest)
        except Exception as e:
            print(f"Error while parsing {closest} from {collection} @ {dt}")
            traceback.print_exception(e)
            return

        try:
            await self.store(main_page, collection, dt)
        except Exception as e:
            print(f"Error while attempting to store {main_page} from {collection} @ {dt}")
            traceback.print_exception(e)
            return


async def main():
    http_client = HttpClient()
    storage = await Storage.create()
    dts = ArchiveDownloader.last_n_days_at_hours(10, [18])

    async with http_client.session() as session:
        ia = InternetArchiveClient(session)
        dler = ArchiveDownloader(storage, ia)

        return await asyncio.gather(
            *[
                dler.handle_snap(c, d)
                for d in dts
                for c in media_collection.values()
            ]
        )


asyncio.run(main())
