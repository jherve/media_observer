from abc import ABC, abstractmethod


class DbConnection(ABC):
    @abstractmethod
    async def __aenter__(self): ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb): ...

    @abstractmethod
    async def execute(self, *args, **kwargs): ...

    @abstractmethod
    async def execute_fetchall(self, *args, **kwargs): ...

    @abstractmethod
    async def execute_insert(self, *args, **kwargs): ...

    @abstractmethod
    async def commit(self): ...
