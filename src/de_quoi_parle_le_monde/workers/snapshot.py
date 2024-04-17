from datetime import date, datetime, time, timedelta
from attrs import frozen
import traceback
from loguru import logger

from de_quoi_parle_le_monde.article import ArchiveCollection
from de_quoi_parle_le_monde.http import HttpSession
from de_quoi_parle_le_monde.internet_archive import (
    InternetArchiveClient,
    SnapshotNotYetAvailable,
)
from de_quoi_parle_le_monde.medias import media_collection
from de_quoi_parle_le_monde.storage import Storage


@frozen
class SnapshotJob:
    collection: ArchiveCollection
    dt: datetime

    @classmethod
    def create(cls, n_days: int, hours: list[int]):
        dts = cls.last_n_days_at_hours(n_days, hours)
        return [cls(c, d) for d in dts for c in media_collection.values()]

    @staticmethod
    def last_n_days_at_hours(n: int, hours: list[int]) -> list[datetime]:
        return [
            datetime.combine(date.today() - timedelta(days=i), time(hour=h))
            for i in range(0, n)
            for h in hours
        ]


@frozen
class SnapshotWorker:
    storage: Storage
    ia_client: InternetArchiveClient

    async def find(self, collection, dt):
        try:
            return await self.ia_client.get_snapshot_id_closest_to(collection.url, dt)
        except SnapshotNotYetAvailable as e:
            logger.warning(f"Snapshot for {collection.name} @ {dt} not yet available")
            raise e
        except Exception as e:
            logger.error(
                f"Error while trying to find snapshot for {collection.name} @ {dt}"
            )
            traceback.print_exception(e)
            raise e

    async def fetch(self, snap_id):
        try:
            return await self.ia_client.fetch(snap_id)
        except Exception as e:
            logger.error(f"Error while fetching {snap_id}")
            traceback.print_exception(e)
            raise e

    async def parse(self, collection, snapshot):
        try:
            return await collection.MainPageClass.from_snapshot(snapshot)
        except Exception as e:
            logger.error(f"Error while parsing {snapshot}")
            traceback.print_exception(e)
            raise e

    async def store(self, page, collection, dt):
        try:
            site_id = await self.storage.add_site(collection.name, collection.url)
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

        except Exception as e:
            logger.error(
                f"Error while attempting to store {page} from {collection.name} @ {dt}"
            )
            traceback.print_exception(e)
            raise e

    async def run(self, job: SnapshotJob):
        collection = job.collection
        dt = job.dt

        if await self.storage.exists_snapshot(collection.name, dt):
            # The snapshot is already stored, skipping
            return

        try:
            logger.info(f"Start handling snap for collection {collection.name} @ {dt}")
            id_closest = await self.find(collection, dt)
            closest = await self.ia_client.fetch(id_closest)
            main_page = await self.parse(collection, closest)
            await self.store(main_page, collection, dt)
            logger.info(f"Snap for collection {collection.name} @ {dt} is stored")
        except Exception:
            return

    @staticmethod
    def create(storage: Storage, session: HttpSession):
        ia = InternetArchiveClient(session)
        return SnapshotWorker(storage, ia)
