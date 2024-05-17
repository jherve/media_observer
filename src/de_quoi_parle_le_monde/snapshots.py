import asyncio
import traceback
import tempfile
import urllib.parse
from pathlib import Path
from datetime import date, datetime, time, timedelta
from attrs import frozen
from loguru import logger


from de_quoi_parle_le_monde.article import ArchiveCollection, MainPage
from de_quoi_parle_le_monde.internet_archive import (
    InternetArchiveClient,
    InternetArchiveSnapshot,
    InternetArchiveSnapshotId,
    SnapshotNotYetAvailable,
)
from de_quoi_parle_le_monde.medias import media_collection
from de_quoi_parle_le_monde.storage import Storage
from de_quoi_parle_le_monde.worker import Job, Worker, JobQueue
from config import settings

idx = 0


def unique_id():
    global idx
    idx = idx + 1
    return idx


@frozen
class SnapshotSearchJob(Job):
    collection: ArchiveCollection
    dt: datetime

    @classmethod
    def create(cls, n_days: int, hours: list[int]):
        dts = cls.last_n_days_at_hours(n_days, hours)
        return [cls(unique_id(), c, d) for d in dts for c in media_collection.values()]

    @staticmethod
    def last_n_days_at_hours(n: int, hours: list[int]) -> list[datetime]:
        now = datetime.now()

        return [
            dt
            for i in range(0, n)
            for h in hours
            if (dt := datetime.combine(date.today() - timedelta(days=i), time(hour=h)))
            < now
        ]

    async def run(self, ia_client: InternetArchiveClient):
        return await ia_client.get_snapshot_id_closest_to(self.collection.url, self.dt)


@frozen
class SnapshotFetchJob(Job):
    snap_id: InternetArchiveSnapshotId
    collection: ArchiveCollection
    dt: datetime

    async def run(self, ia_client: InternetArchiveClient):
        return await ia_client.fetch(self.snap_id)


@frozen
class SnapshotParseJob(Job):
    collection: ArchiveCollection
    snapshot: InternetArchiveSnapshot
    dt: datetime

    async def run(self):
        return await self.collection.MainPageClass.from_snapshot(self.snapshot)


@frozen
class SnapshotStoreJob(Job):
    page: MainPage
    collection: ArchiveCollection
    dt: datetime

    async def run(self, storage: Storage):
        return await storage.add_page(self.collection, self.page, self.dt)


@frozen
class SearchWorker(Worker):
    storage: Storage
    ia_client: InternetArchiveClient
    type_ = SnapshotSearchJob

    async def execute(self, job: SnapshotSearchJob):
        collection = job.collection
        dt = job.dt

        if await self.storage.exists_snapshot(collection.name, dt):
            return None, []

        self._log(
            "DEBUG", job, f"Start handling snap for collection {collection.name} @ {dt}"
        )

        try:
            id_closest = await job.run(self.ia_client)
            return id_closest, [
                SnapshotFetchJob(job.id_, id_closest, job.collection, job.dt)
            ]

        except SnapshotNotYetAvailable as e:
            self._log(
                "WARNING",
                job,
                f"Snapshot for {collection.name} @ {dt} not yet available",
            )
            raise e

        except Exception as e:
            self._log(
                "ERROR",
                job,
                f"Error while trying to find snapshot for {collection.name} @ {dt}",
            )
            traceback.print_exception(e)
            raise e


@frozen
class FetchWorker(Worker):
    ia_client: InternetArchiveClient
    type_ = SnapshotFetchJob

    async def execute(self, job: SnapshotFetchJob):
        try:
            closest = await job.run(self.ia_client)
            return closest, [SnapshotParseJob(job.id_, job.collection, closest, job.dt)]
        except Exception as e:
            self._log("ERROR", job, f"Error while fetching {job.snap_id}")
            traceback.print_exception(e)
            raise e


@frozen
class ParseWorker(Worker):
    type_ = SnapshotParseJob

    async def execute(self, job: SnapshotParseJob):
        try:
            main_page = await job.run()
            return main_page, [
                SnapshotStoreJob(job.id_, main_page, job.collection, job.dt)
            ]
        except Exception as e:
            snapshot = job.snapshot
            tmpdir_prefix = urllib.parse.quote_plus(
                f"le_monde_{snapshot.id.original}_{snapshot.id.timestamp}"
            )
            tmpdir = Path(tempfile.mkdtemp(prefix=tmpdir_prefix))

            with open(tmpdir / "snapshot.html", "w") as f:
                f.write(snapshot.text)
            with open(tmpdir / "exception.txt", "w") as f:
                f.writelines(traceback.format_exception(e))
            with open(tmpdir / "url.txt", "w") as f:
                f.write(snapshot.id.url)

            self._log(
                "ERROR",
                job,
                f"Error while parsing snapshot from {snapshot.id.url}, details were written in directory {tmpdir}",
            )
            raise e


@frozen
class StoreWorker(Worker):
    storage: Storage
    type_ = SnapshotStoreJob

    async def execute(self, job: SnapshotStoreJob):
        try:
            return await job.run(self.storage), []
        except Exception as e:
            self._log(
                "ERROR",
                job,
                f"Error while attempting to store {job.page} from {job.collection.name} @ {job.dt}",
            )
            traceback.print_exception(e)
            raise e


async def main():
    storage = await Storage.create()

    queue = JobQueue(
        [
            SnapshotSearchJob,
            SnapshotFetchJob,
            SnapshotParseJob,
            SnapshotStoreJob,
        ]
    )

    logger.info("Starting snapshot service..")
    jobs = SnapshotSearchJob.create(
        settings.snapshots.days_in_past, settings.snapshots.hours
    )

    for j in jobs:
        queue.put_nowait(j)

    async with InternetArchiveClient.create() as ia:
        workers = {
            SearchWorker(queue, storage, ia): 3,
            FetchWorker(queue, ia): 3,
            ParseWorker(queue): 3,
            StoreWorker(queue, storage): 3,
        }

        async with asyncio.TaskGroup() as tg:
            tasks = []
            for w, nb in workers.items():
                for _ in range(nb):
                    tasks.append(tg.create_task(w.loop()))

            # Wait until the queue is fully processed.
            await queue.join()

            for t in tasks:
                t.cancel()

    logger.info("Snapshot service exiting")


if __name__ == "__main__":
    asyncio.run(main())
