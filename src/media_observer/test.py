import asyncio
from datetime import date, datetime, time, timedelta
import traceback
from zoneinfo import ZoneInfo
from loguru import logger
from attrs import frozen
from abc import ABC, abstractmethod
from uuid import UUID, uuid1

from media_observer.article import ArchiveCollection
from media_observer.internet_archive import (
    InternetArchiveClient,
    SnapshotNotYetAvailable,
)
from media_observer.storage import Storage
from media_observer.medias import media_collection
from config import settings


@frozen
class Job(ABC):
    id_: UUID

    @abstractmethod
    async def execute(self, **kwargs): ...

    def _log(self, level: str, msg: str):
        logger.log(level, f"[{self.id_}] {msg}")


class StupidJob(Job):
    async def execute(self, *args, **kwargs):
        logger.info(f"Executing job {self.id_}..")


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

    async def execute(self, *, storage: Storage, ia_client: InternetArchiveClient):
        collection = self.collection
        dt = self.dt

        if await storage.exists_frontpage(collection.name, dt):
            return None, []

        self._log(
            "DEBUG",
            f"Start handling snap for collection {collection.name} @ {dt}",
        )

        try:
            id_closest = await ia_client.get_snapshot_id_closest_to(
                self.collection.url, self.dt
            )

            delta = self.dt - id_closest.timestamp
            abs_delta = abs(delta)
            if abs_delta.total_seconds() > 3600:
                time = "after" if delta > timedelta(0) else "before"
                self._log(
                    "WARNING",
                    f"Snapshot is {abs(delta)} {time} the required timestamp ({id_closest.timestamp} instead of {self.dt})",
                )

            self._log("INFO", f"Got snapshot {id_closest}")
            return id_closest, [(self.id_, id_closest, self.collection, self.dt)]

        except SnapshotNotYetAvailable as e:
            self._log(
                "WARNING",
                f"Snapshot for {collection.name} @ {dt} not yet available",
            )
            raise e

        except Exception as e:
            self._log(
                "ERROR",
                f"Error while trying to find snapshot for {collection.name} @ {dt}",
            )
            traceback.print_exception(e)
            raise e


@frozen
class Worker:
    i: int

    async def loop(self):
        logger.info(f"Hello from task #{self.i}")
        while True:
            try:
                await self.run()
            except asyncio.CancelledError:
                logger.warning(f"Task #{self.i} cancelled")
                return
            except Exception as e:
                logger.error(f"Task #{self.i} failed with #{e}")

    async def run(self):
        await asyncio.sleep(1)
        logger.info(f"Task #{self.i} doing stuff")

    def get_execution_context(self) -> dict: ...


@frozen
class QueueWorker(Worker):
    queue: asyncio.Queue

    async def run(self):
        logger.info(f"Task #{self.i} waiting for job..")
        job: Job = await self.queue.get()
        assert isinstance(job, Job)
        await job.execute(**self.get_execution_context())
        self.queue.task_done()

    def get_execution_context(self):
        return {}


@frozen
class SnapshotWorker(QueueWorker):
    storage: Storage
    ia_client: InternetArchiveClient

    def get_execution_context(self):
        return {"storage": self.storage, "ia_client": self.ia_client}


queues = [asyncio.Queue() for _ in range(0, 2)]
snap_queue = asyncio.Queue()


async def main():
    logger.info("Hello world")
    tasks = []
    jobs = SnapshotSearchJob.create(
        settings.snapshots.days_in_past, settings.snapshots.hours
    )
    storage = await Storage.create()
    try:
        async with InternetArchiveClient.create() as ia:
            worker = SnapshotWorker(15, snap_queue, storage, ia)
            async with asyncio.TaskGroup() as tg:
                for i in range(0, 2):
                    w = Worker(i)
                    tasks.append(tg.create_task(w.loop()))
                for i in range(0, 2):
                    qw = QueueWorker(i, queue=queues[i])
                    tasks.append(tg.create_task(qw.loop()))
                for q in queues:
                    job = StupidJob(uuid1())
                    await q.put(job)

                tasks.append(tg.create_task(worker.loop()))
                for j in jobs[:3]:
                    await snap_queue.put(j)
    finally:
        await storage.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Main kbinterrupt")
