import asyncio
from loguru import logger
from attrs import frozen
from abc import ABC, abstractmethod
from uuid import UUID, uuid1


@frozen
class Job(ABC):
    id_: UUID

    @abstractmethod
    async def execute(self, *args, **kwargs): ...


class StupidJob(Job):
    async def execute(self, *args, **kwargs):
        logger.info(f"Executing job {self.id_}..")


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
        job: Job = await self.queue.get()
        assert isinstance(job, Job)
        await job.execute()
        self.queue.task_done()


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
        for q in queues:
            job = StupidJob(uuid1())
            await q.put(job)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Main kbinterrupt")
