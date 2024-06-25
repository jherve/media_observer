import asyncio
from itertools import islice
from datetime import date, datetime, time, timedelta
import os
from pathlib import Path
import pickle
import tempfile
import traceback
from typing import Any, ClassVar
import urllib.parse
from zoneinfo import ZoneInfo
from loguru import logger
from attrs import field, frozen
from abc import ABC, abstractmethod
from uuid import UUID, uuid1
from hypercorn.asyncio import serve
from hypercorn.config import Config

from media_observer.article import ArchiveCollection, FrontPage
from media_observer.internet_archive import (
    InternetArchiveClient,
    InternetArchiveSnapshot,
    InternetArchiveSnapshotId,
    SnapshotNotYetAvailable,
)
from media_observer.similarity_index import SimilaritySearch
from media_observer.storage import Storage
from media_observer.medias import media_collection
from media_observer.web import app
from config import settings


tmpdir = Path(tempfile.mkdtemp(prefix="media_observer"))


@frozen
class Job(ABC):
    id_: UUID
    queue: ClassVar[asyncio.Queue]

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
class Worker(ABC):
    async def loop(self):
        logger.info(f"Task {self.__class__.__name__} {id(self)} booting..")
        while True:
            try:
                await self.run()
            except asyncio.CancelledError:
                logger.warning(f"Task {self.__class__.__name__} {id(self)} cancelled")
                return
            except Exception as e:
                traceback.print_exception(e)
                logger.error(
                    f"Task {self.__class__.__name__} {id(self)} failed with {e}"
                )

    @abstractmethod
    async def run(self): ...

    def get_execution_context(self) -> dict: ...


@frozen
class QueueWorker(Worker):
    inbound_queue: asyncio.Queue
    outbound_queue: asyncio.Queue | None

    async def run(self):
        logger.info(f"Task {self.__class__.__name__} {id(self)} waiting for job..")
        job: Job = await self.inbound_queue.get()
        assert isinstance(job, Job)

        ret, further_jobs = await job.execute(**self.get_execution_context())
        try:
            for j in further_jobs:
                await self.outbound_queue.put(j)
        except AttributeError as e:
            logger.error(
                f"Could not push jobs {further_jobs} because there is no outbound queue"
            )
            raise (e)
        self.inbound_queue.task_done()

    def get_execution_context(self):
        return {}


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
class ParseWorker(QueueWorker): ...


@frozen
class StoreWorker(QueueWorker):
    storage: Storage

    def get_execution_context(self):
        return {"storage": self.storage}


def batched(iterable, n):
    """
    Batch data into tuples of length n. The last batch may be shorter.
        `batched('ABCDEFG', 3) --> ABC DEF G`

    Straight from : https://docs.python.org/3.11/library/itertools.html#itertools-recipes
    """
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


@frozen
class EmbeddingsWorker(Worker):
    storage: Storage
    model_name: str
    batch_size: int
    model: Any = field(init=False, default=None)

    async def run(self):
        def load_model():
            from sentence_transformers import SentenceTransformer

            # Quite a dirty trick since the instance is supposed to be "frozen"
            # but I did not find a better solution to load the model in the
            # background
            object.__setattr__(self, "model", SentenceTransformer(self.model_name))

        def compute_embeddings_for(sentences: tuple[tuple[int, str]]):
            logger.debug(f"Computing embeddings for {len(sentences)} sentences")
            all_texts = [t[1] for t in sentences]
            all_embeddings = self.model.encode(all_texts)

            return {sentences[idx][0]: e for idx, e in enumerate(all_embeddings)}

        loop = asyncio.get_running_loop()
        if self.model is None:
            await loop.run_in_executor(None, load_model)

        all_titles = [
            (t["id"], t["text"])
            for t in await self.storage.list_all_titles_without_embedding()
        ]

        for batch in batched(all_titles, self.batch_size):
            embeddings = compute_embeddings_for(batch)
            for i, embed in embeddings.items():
                await self.storage.add_embedding(i, embed)

            logger.debug(f"Stored {len(embeddings)} embeddings")

        await asyncio.sleep(5)


@frozen
class SimilarityIndexWorker(Worker):
    storage: Storage

    async def run(self):
        sim_index = SimilaritySearch.create(self.storage)

        logger.info("Starting index..")
        await sim_index.add_embeddings()
        await sim_index.save()
        logger.info("Similarity index ready")


@frozen
class WebServer(Worker):
    async def run(self):
        shutdown_event = asyncio.Event()

        try:
            logger.info("Web server stuff")
            # Just setting the shutdown_trigger even though it is not connected
            # to anything allows the app to gracefully shutdown
            await serve(app, Config(), shutdown_trigger=shutdown_event.wait)
        except asyncio.CancelledError:
            logger.warning("Web server exiting")
            return


async def main():
    tasks = []
    jobs = SnapshotSearchJob.create(
        settings.snapshots.days_in_past, settings.snapshots.hours
    )
    storage = await Storage.create()
    try:
        async with InternetArchiveClient.create() as ia:
            workers = {
                "snapshot": SnapshotWorker(
                    SnapshotSearchJob.queue, SnapshotFetchJob.queue, storage, ia
                ),
                "fetch": FetchWorker(
                    SnapshotFetchJob.queue, SnapshotParseJob.queue, ia
                ),
                "parse": ParseWorker(SnapshotParseJob.queue, SnapshotStoreJob.queue),
                "store": StoreWorker(SnapshotStoreJob.queue, None, storage),
            }
            web_server = WebServer()
            embeds = EmbeddingsWorker(
                storage,
                "dangvantuan/sentence-camembert-large",
                64,
            )
            index = SimilarityIndexWorker(storage)
            async with asyncio.TaskGroup() as tg:
                for w in workers.values():
                    tasks.append(tg.create_task(w.loop()))
                for j in jobs:
                    await SnapshotSearchJob.queue.put(j)

                tasks.append(tg.create_task(web_server.run()))
                tasks.append(tg.create_task(embeds.loop()))
                tasks.append(tg.create_task(index.run()))
    finally:
        await storage.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Main kbinterrupt")
