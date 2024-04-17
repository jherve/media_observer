import asyncio
from hypercorn.typing import Framework
from loguru import logger
from hypercorn.config import Config
from hypercorn.asyncio import serve
from attrs import frozen


from de_quoi_parle_le_monde.web import app
from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.storage import Storage
from de_quoi_parle_le_monde.workers.snapshot import SnapshotJob, SnapshotWorker
from de_quoi_parle_le_monde.workers.embeddings import (
    EmbeddingsJob,
    EmbeddingsWorker,
)
from de_quoi_parle_le_monde.similarity_search import SimilaritySearch


@frozen
class Application:
    http_client: HttpClient
    storage: Storage
    web_app: Framework
    web_config: Config
    similarity_index: SimilaritySearch

    async def run(self):
        await asyncio.gather(
            self._run_web_server(),
            self._run_snapshot_worker(),
            self._run_similarity_index(),
            self._run_embeddings_worker(),
        )
        logger.info("Will quit now..")

    async def _run_web_server(self):
        logger.info("Starting web server..")
        await serve(self.web_app, self.web_config)
        logger.info("Web server exiting")

    async def _run_snapshot_worker(self):
        logger.info("Starting snapshot service..")
        jobs = SnapshotJob.create(10, [8, 12, 18, 22])

        async with self.http_client.session() as session:
            worker = SnapshotWorker.create(self.storage, session)
            await asyncio.gather(*[worker.run(job) for job in jobs])
        logger.info("Snapshot service exiting")

    async def _run_embeddings_worker(self):
        logger.info("Starting embeddings service..")
        jobs = await EmbeddingsJob.create(self.storage)
        if jobs:
            loop = asyncio.get_event_loop()
            worker = await loop.run_in_executor(
                None,
                EmbeddingsWorker.create,
                self.storage,
                "dangvantuan/sentence-camembert-large",
            )
            await worker.run(jobs)

        logger.info("Embeddings service exiting")

    async def _run_similarity_index(self):
        logger.info("Starting index..")
        try:
            await self.similarity_index.add_embeddings()
            logger.info("Similarity index ready")
        except ValueError:
            ...

    @staticmethod
    async def create():
        http_client = HttpClient()
        storage = await Storage.create()
        web_app = app
        web_config = Config()
        sim_index = SimilaritySearch.create(storage)

        return Application(http_client, storage, web_app, web_config, sim_index)


async def main():
    full_application = await Application.create()
    await full_application.run()


if __name__ == "__main__":
    asyncio.run(main())
