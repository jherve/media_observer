import asyncio
from loguru import logger
from attrs import frozen


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

    async def run(self):
        await asyncio.sleep(1)
        logger.info(f"Task #{self.i} doing stuff")


async def main():
    logger.info("Hello world")
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for i in range(0, 2):
            w = Worker(i)
            tasks.append(tg.create_task(w.loop()))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Main kbinterrupt")
