import asyncio
from loguru import logger
from attrs import frozen
from hypercorn.asyncio import serve
from hypercorn.config import Config

from media_observer.worker import Worker
from media_observer.embeddings import EmbeddingsWorker
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
from media_observer.similarity_index import SimilarityIndexWorker
from media_observer.storage import Storage
from media_observer.web import app


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
