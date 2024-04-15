import asyncio

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.storage import Storage
from de_quoi_parle_le_monde.snapshot_worker import download_all, compute_embeddings


async def main():
    http_client = HttpClient()
    storage = await Storage.create()

    # await download_all(http_client, storage, 10, [18])
    await compute_embeddings(storage)


asyncio.run(main())
