import asyncio
from loguru import logger


from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.storage import Storage
from de_quoi_parle_le_monde.workers.snapshot import SnapshotJob, SnapshotWorker


async def main():
    http_client = HttpClient()
    storage = await Storage.create()

    logger.info("Starting snapshot service..")
    jobs = SnapshotJob.create(10, [8, 12, 18, 22])

    async with http_client.session() as session:
        worker = SnapshotWorker.create(storage, session)
        await asyncio.gather(*[worker.run(job) for job in jobs])
    logger.info("Snapshot service exiting")


if __name__ == "__main__":
    asyncio.run(main())
