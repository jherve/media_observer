import asyncio
from attrs import frozen
from loguru import logger
from abc import ABC, abstractmethod
from typing import Any, ClassVar


@frozen
class Job(ABC):
    id_: int

    @abstractmethod
    async def run(self, *args): ...


class JobQueue:
    def __init__(self, job_types) -> None:
        self.job_types = job_types
        self._finished = asyncio.locks.Event()
        self._pending_tasks = 0
        self.queues = {kls: asyncio.Queue() for kls in self.job_types}

    async def get(self, job_kls):
        return await self.queues[job_kls].get()

    def task_done(self, job_kls):
        self.queues[job_kls].task_done()

        self._pending_tasks -= 1
        if self._pending_tasks == 0:
            self._finished.set()

    def put_nowait(self, job):
        self._pending_tasks += 1
        self._finished.clear()
        return self.queues[type(job)].put_nowait(job)

    async def join(self):
        if self._pending_tasks > 0:
            await self._finished.wait()

    def qsize(self):
        return {j: self.queues[j].qsize() for j in self.job_types}


@frozen
class Worker(ABC):
    queue: JobQueue
    type_: ClassVar[type]

    @abstractmethod
    async def execute(self, job: Job) -> tuple[Any, list[Job]]: ...

    async def loop(self):
        while True:
            # Get a "work item" out of the queue.
            job = await self.queue.get(self.type_)

            assert isinstance(job, self.type_)

            try:
                res, further_jobs = await self.execute(job)

                if res is not None:
                    self._log("DEBUG", job, f"Completed job {job.__class__.__name__}")

                for j in further_jobs:
                    self.queue.put_nowait(j)
            except Exception:
                ...

            self.queue.task_done(self.type_)

    def _log(self, level: str, job: Job, msg: str):
        logger.log(level, f"[{job.id_: <3}] {msg}")
