import asyncio
from loguru import logger


from de_quoi_parle_le_monde.storage import Storage
from de_quoi_parle_le_monde.workers.embeddings import (
    EmbeddingsJob,
    EmbeddingsWorker,
)


async def main():
    storage = await Storage.create()

    logger.info("Starting embeddings service..")
    jobs = await EmbeddingsJob.create(storage)
    if jobs:
        loop = asyncio.get_event_loop()
        worker = await loop.run_in_executor(
            None,
            EmbeddingsWorker.create,
            storage,
            "dangvantuan/sentence-camembert-large",
        )
        await worker.run(jobs)

    logger.info("Embeddings service exiting")


if __name__ == "__main__":
    asyncio.run(main())
