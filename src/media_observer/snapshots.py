import asyncio
from datetime import date, datetime, time, timedelta
import os
from pathlib import Path
import pickle
import tempfile
import traceback
import urllib.parse
from zoneinfo import ZoneInfo
from attrs import frozen
from uuid import uuid1

from media_observer.worker import Job, Worker, QueueWorker
from media_observer.article import ArchiveCollection, FrontPage
from media_observer.internet_archive import (
    InternetArchiveClient,
    InternetArchiveSnapshot,
    InternetArchiveSnapshotId,
    SnapshotNotYetAvailable,
)
from media_observer.storage import Storage
from media_observer.medias import media_collection
from config import settings


tmpdir = Path(tempfile.mkdtemp(prefix="media_observer"))


def unique_id():
    return uuid1()


@frozen
class SnapshotSearchJob(Job):
    queue = asyncio.Queue()
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
            return id_closest, [
                SnapshotFetchJob(self.id_, id_closest, self.collection, self.dt)
            ]

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
class SnapshotFetchJob(Job):
    queue = asyncio.Queue()
    snap_id: InternetArchiveSnapshotId
    collection: ArchiveCollection
    dt: datetime

    async def execute(self, ia_client: InternetArchiveClient):
        try:
            closest = await ia_client.fetch(self.snap_id)
            return closest, [
                SnapshotParseJob(self.id_, self.collection, closest, self.dt)
            ]
        except Exception as e:
            self._log("ERROR", f"Error while fetching {self.snap_id}")
            traceback.print_exception(e)
            raise e


@frozen
class SnapshotParseJob(Job):
    queue = asyncio.Queue()
    collection: ArchiveCollection
    snapshot: InternetArchiveSnapshot
    dt: datetime

    async def execute(self):
        try:
            main_page = await self.collection.FrontPageClass.from_snapshot(
                self.snapshot
            )
            return main_page, [
                SnapshotStoreJob(self.id_, main_page, self.collection, self.dt)
            ]
        except Exception as e:
            snapshot = self.snapshot
            sub_dir = (
                tmpdir
                / urllib.parse.quote_plus(snapshot.id.original)
                / urllib.parse.quote_plus(str(snapshot.id.timestamp))
            )
            os.makedirs(sub_dir)

            with open(sub_dir / "self.pickle", "wb") as f:
                pickle.dump(self, f)
            with open(sub_dir / "snapshot.html", "w") as f:
                f.write(snapshot.text)
            with open(sub_dir / "exception.txt", "w") as f:
                f.writelines(traceback.format_exception(e))
            with open(sub_dir / "url.txt", "w") as f:
                f.write(snapshot.id.url)

            self._log(
                "ERROR",
                f"Error while parsing snapshot from {snapshot.id.url}, details were written in directory {sub_dir}",
            )
            raise e


@frozen
class SnapshotStoreJob(Job):
    queue = asyncio.Queue()
    page: FrontPage
    collection: ArchiveCollection
    dt: datetime

    async def execute(self, storage: Storage):
        try:
            return await storage.add_page(self.collection, self.page, self.dt), []
        except Exception as e:
            self._log(
                "ERROR",
                f"Error while attempting to store {self.page} from {self.collection.name} @ {self.dt}",
            )
            traceback.print_exception(e)
            raise e


@frozen
class SnapshotWatchdog(Worker):
    snapshot_queue: asyncio.Queue

    async def run(self):
        await self._push_new_jobs()

        while True:
            sleep_time_s = self._seconds_until_next_full_hour()
            await asyncio.sleep(sleep_time_s)
            self._log("INFO", f"Woke up at {datetime.now()}")
            await self._push_new_jobs()

    async def _push_new_jobs(self):
        initial_jobs = SnapshotSearchJob.create(
            settings.snapshots.days_in_past, settings.snapshots.hours
        )
        for j in initial_jobs:
            await self.snapshot_queue.put(j)

    @staticmethod
    def _seconds_until_next_full_hour() -> float:
        now = datetime.now()
        next_tick = timedelta(
            hours=1,
            minutes=-now.minute,
            seconds=-now.second,
            microseconds=-now.microsecond,
        )
        return next_tick / timedelta(microseconds=1) / 1e6


@frozen
class SnapshotWorker(QueueWorker):
    storage: Storage
    ia_client: InternetArchiveClient

    def get_execution_context(self):
        return {"storage": self.storage, "ia_client": self.ia_client}


@frozen
class FetchWorker(QueueWorker):
    ia_client: InternetArchiveClient

    def get_execution_context(self):
        return {"ia_client": self.ia_client}


@frozen
class ParseWorker(QueueWorker):
    def get_execution_context(self):
        return {}


@frozen
class StoreWorker(QueueWorker):
    storage: Storage

    def get_execution_context(self):
        return {"storage": self.storage}
