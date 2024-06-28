import asyncio
from uuid import UUID
from attrs import frozen
from loguru import logger
from abc import ABC, abstractmethod
from typing import ClassVar


@frozen
class Job(ABC):
    id_: UUID
    queue: ClassVar[asyncio.Queue]

    @abstractmethod
    async def execute(self, **kwargs): ...

    def _log(self, level: str, msg: str):
        logger.log(level, f"[{self.id_}] {msg}")


class Worker(ABC):
    @abstractmethod
    async def run(self): ...

    def _log(self, level: str, msg: str):
        logger.log(level, f"[Worker {self.__class__.__name__}] {msg}")


@frozen
class QueueWorker(Worker):
    inbound_queue: asyncio.Queue
    outbound_queue: asyncio.Queue | None

    async def run(self):
        self._log("INFO", "booting..")
        while True:
            try:
                await self.step()
            except asyncio.CancelledError:
                self._log("WARNING", "cancelled")
                return
            except Exception as e:
                self._log("DEBUG", f"failed with {e.__class__.__name__}")

    async def step(self):
        job: Job = await self.inbound_queue.get()
        assert isinstance(job, Job)

        ret, further_jobs = await job.execute(**self.get_execution_context())
        if self.outbound_queue is not None:
            for j in further_jobs:
                await self.outbound_queue.put(j)
        elif further_jobs:
            self._log(
                "ERROR",
                f"Could not push {len(further_jobs)} jobs because there is no outbound queue",
            )
        self.inbound_queue.task_done()

    @abstractmethod
    def get_execution_context(self) -> dict: ...
