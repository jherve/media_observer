import asyncio
from loguru import logger
from hypercorn.config import Config
from hypercorn.asyncio import serve


from de_quoi_parle_le_monde.web import app
from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.storage import Storage


async def main():
    http_client = HttpClient()
    storage = await Storage.create()

    await serve(app, Config())
    logger.info("Will quit now..")


asyncio.run(main())
