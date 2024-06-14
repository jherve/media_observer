import asyncio
from uuid import uuid1
import traceback
import os
import tempfile
import urllib.parse
from pathlib import Path
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from attrs import frozen
from loguru import logger


from media_observer.article import ArchiveCollection, FrontPage
from media_observer.internet_archive import (
    InternetArchiveClient,
    InternetArchiveSnapshot,
    InternetArchiveSnapshotId,
    SnapshotNotYetAvailable,
)
from media_observer.medias import media_collection
from media_observer.storage import Storage
from media_observer.worker import Job, Worker, JobQueue
from config import settings


tmpdir = Path(tempfile.mkdtemp(prefix="media_observer"))
idx = 0


def unique_id():
    return uuid1()


@frozen
class SnapshotSearchJob(Job):
    collection: ArchiveCollection
    dt: datetime

    @classmethod
    def create(cls, n_days: int, hours: list[int]):
        return [
            cls(unique_id(), c, d)
            for c in media_collection.values()
            for d in cls.last_n_days_at_hours(n_days, hours, c.tz)
        ]

    @staticmethod
    def last_n_days_at_hours(n: int, hours: list[int], tz: ZoneInfo) -> list[datetime]:
        now = datetime.now(tz)

        return [
            dt
            for i in range(0, n)
            for h in hours
            if (
                dt := datetime.combine(
                    date.today() - timedelta(days=i), time(hour=h), tzinfo=tz
                )
            )
            < now
        ]


@frozen
class SnapshotFetchJob(Job):
    snap_id: InternetArchiveSnapshotId
    collection: ArchiveCollection
    dt: datetime


@frozen
class SnapshotParseJob(Job):
    collection: ArchiveCollection
    snapshot: InternetArchiveSnapshot
    dt: datetime


@frozen
class SnapshotStoreJob(Job):
    page: FrontPage
    collection: ArchiveCollection
    dt: datetime


@frozen
class SearchWorker(Worker):
    storage: Storage
    ia_client: InternetArchiveClient
    type_ = SnapshotSearchJob

    async def execute(self, job: SnapshotSearchJob):
        collection = job.collection
        dt = job.dt

        if await self.storage.exists_frontpage(collection.name, dt):
            return None, []

        self._log(
            "DEBUG", job, f"Start handling snap for collection {collection.name} @ {dt}"
        )

        try:
            id_closest = await self.ia_client.get_snapshot_id_closest_to(
                job.collection.url, job.dt
            )

            delta = job.dt - id_closest.timestamp
            abs_delta = abs(delta)
            if abs_delta.total_seconds() > 3600:
                time = "after" if delta > timedelta(0) else "before"
                self._log(
                    "WARNING",
                    job,
                    f"Snapshot is {abs(delta)} {time} the required timestamp ({id_closest.timestamp} instead of {job.dt})",
                )

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
            closest = await self.ia_client.fetch(job.snap_id)
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
            main_page = await job.collection.FrontPageClass.from_snapshot(job.snapshot)
            return main_page, [
                SnapshotStoreJob(job.id_, main_page, job.collection, job.dt)
            ]
        except Exception as e:
            snapshot = job.snapshot
            sub_dir = (
                tmpdir
                / urllib.parse.quote_plus(snapshot.id.original)
                / urllib.parse.quote_plus(str(snapshot.id.timestamp))
            )
            os.makedirs(sub_dir)

            with open(sub_dir / "snapshot.html", "w") as f:
                f.write(snapshot.text)
            with open(sub_dir / "exception.txt", "w") as f:
                f.writelines(traceback.format_exception(e))
            with open(sub_dir / "url.txt", "w") as f:
                f.write(snapshot.id.url)

            self._log(
                "ERROR",
                job,
                f"Error while parsing snapshot from {snapshot.id.url}, details were written in directory {sub_dir}",
            )
            raise e


@frozen
class StoreWorker(Worker):
    storage: Storage
    type_ = SnapshotStoreJob

    async def execute(self, job: SnapshotStoreJob):
        try:
            return await self.storage.add_page(job.collection, job.page, job.dt), []
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
            StoreWorker(queue, storage): 1,
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

    await storage.close()
    logger.info("Snapshot service exiting")


if __name__ == "__main__":
    asyncio.run(main())
