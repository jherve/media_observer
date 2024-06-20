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


@frozen
class QueueWorker(Worker):
    queue: asyncio.Queue

    async def run(self):
        logger.info(f"Task #{self.i} waiting for job..")
        job = await self.queue.get()
        await self.execute_job(job)
        self.queue.task_done()

    async def execute_job(self, job):
        logger.info(f"Executing job {job}..")


queues = [asyncio.Queue() for _ in range(0, 2)]


async def main():
    logger.info("Hello world")
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for i in range(0, 2):
            w = Worker(i)
            tasks.append(tg.create_task(w.loop()))
        for i in range(0, 2):
            qw = QueueWorker(i, queue=queues[i])
            tasks.append(tg.create_task(qw.loop()))
        for idx, q in enumerate(queues):
            await q.put({"test": idx})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Main kbinterrupt")
