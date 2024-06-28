import asyncio
import concurrent.futures
from itertools import islice
from typing import Any
from loguru import logger
from attrs import define, field, frozen
from hypercorn.asyncio import serve
from hypercorn.config import Config

from media_observer.worker import Worker
from media_observer.internet_archive import InternetArchiveClient
from media_observer.snapshots import (
    FetchWorker,
    ParseWorker,
    SnapshotWorker,
    SnapshotFetchJob,
    SnapshotParseJob,
    SnapshotStoreJob,
    SnapshotWatchdog,
    StoreWorker,
    SnapshotSearchJob,
)
from media_observer.similarity_index import SimilaritySearch
from media_observer.storage import Storage
from media_observer.web import app


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


@define
class EmbeddingsWorker(Worker):
    storage: Storage
    model_name: str
    batch_size: int
    new_embeddings_event: asyncio.Event
    model: Any = field(init=False, default=None)

    async def run(self):
        def load_model():
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)

        while True:
            loop = asyncio.get_running_loop()
            if self.model is None:
                await loop.run_in_executor(None, load_model)

            all_titles = [
                (t["id"], t["text"])
                for t in await self.storage.list_all_titles_without_embedding()
            ]

            for batch in batched(all_titles, self.batch_size):
                with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
                    embeddings = await loop.run_in_executor(
                        pool, self.compute_embeddings_for, self.model, batch
                    )
                for i, embed in embeddings.items():
                    await self.storage.add_embedding(i, embed)

                logger.debug(f"Stored {len(embeddings)} embeddings")

                if embeddings:
                    self.new_embeddings_event.set()

            await asyncio.sleep(5)

    @staticmethod
    def compute_embeddings_for(model: Any, sentences: tuple[tuple[int, str]]):
        logger.debug(f"Computing embeddings for {len(sentences)} sentences")
        all_texts = [t[1] for t in sentences]
        all_embeddings = model.encode(all_texts)

        return {sentences[idx][0]: e for idx, e in enumerate(all_embeddings)}


@frozen
class SimilarityIndexWorker(Worker):
    storage: Storage
    new_embeddings_event: asyncio.Event

    async def run(self):
        while True:
            await self.new_embeddings_event.wait()

            sim_index = SimilaritySearch.create(self.storage)
            logger.info("Starting index..")
            await sim_index.add_embeddings()
            await sim_index.save()
            logger.info("Similarity index ready")

            self.new_embeddings_event.clear()


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


@frozen
class MediaObserverApplication:
    snapshots_workers: list[Worker]
    web_server: WebServer
    embeds: EmbeddingsWorker
    index: SimilarityIndexWorker

    @property
    def workers(self):
        return self.snapshots_workers + [self.web_server, self.embeds, self.index]

    @staticmethod
    async def create(storage: Storage, ia: InternetArchiveClient):
        new_embeddings_event = asyncio.Event()
        new_embeddings_event.set()

        snapshots_workers = (
            [SnapshotWatchdog(SnapshotSearchJob.queue)]
            + [
                SnapshotWorker(
                    SnapshotSearchJob.queue, SnapshotFetchJob.queue, storage, ia
                )
            ]
            * 3
            + [FetchWorker(SnapshotFetchJob.queue, SnapshotParseJob.queue, ia)] * 3
            + [
                ParseWorker(SnapshotParseJob.queue, SnapshotStoreJob.queue),
                StoreWorker(SnapshotStoreJob.queue, None, storage),
            ]
        )
        web_server = WebServer()
        embeds = EmbeddingsWorker(
            storage,
            "dangvantuan/sentence-camembert-large",
            64,
            new_embeddings_event,
        )
        index = SimilarityIndexWorker(storage, new_embeddings_event)
        return MediaObserverApplication(snapshots_workers, web_server, embeds, index)


async def main():
    tasks = []
    storage = await Storage.create()

    try:
        async with InternetArchiveClient.create() as ia:
            app = await MediaObserverApplication.create(storage, ia)

            async with asyncio.TaskGroup() as tg:
                for w in app.workers:
                    tasks.append(tg.create_task(w.run()))

    finally:
        await storage.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Main kbinterrupt")
