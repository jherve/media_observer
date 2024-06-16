from abc import ABC
from enum import Enum, auto
from datetime import datetime
from attrs import frozen


@frozen
class UniqueIndex:
    table: str
    columns: list[str]

    @property
    def name(self):
        return f"{self.table}_unique_idx_{'_'.join(self.columns)}"

    async def create_if_not_exists(self, conn):
        cols = ",".join(self.columns)
        stmt = f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self.name}
            ON {self.table} ({cols})
        """
        await conn.execute(stmt)


@frozen
class Reference:
    table_name: str
    column_name: str
    on_delete: str | None = None

    @property
    def as_sql(self):
        on_delete = "ON DELETE CASCADE" if self.on_delete == "cascade" else None
        return f"{self.table_name} ({self.column_name}) {on_delete}"


class ColumnType(Enum):
    PrimaryKey = "SERIAL PRIMARY KEY"
    References = "REFERENCES"
    Text = "TEXT"
    Url = "TEXT"
    TimestampTz = "timestamp with time zone"
    Integer = "INTEGER"
    Vector = "bytea"


@frozen
class Column:
    name: str
    type_: ColumnType | None = None
    primary_key: bool = False
    references: Reference | None = None

    @property
    def attrs(self):
        if self.primary_key:
            return ColumnType.PrimaryKey.value
        elif self.references is not None:
            return f"{ColumnType.Integer.value} {ColumnType.References.value} {self.references.as_sql}"
        elif self.type_ is not None:
            return self.type_.value
        else:
            raise ValueError("Missing informations in column")


@frozen
class Table:
    name: str
    columns: list[Column]

    @property
    def column_names(self):
        return [c.name for c in self.columns]

    async def create_if_not_exists(self, conn):
        cols = ",\n".join([f"{c.name} {c.attrs}" for c in self.columns])
        await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.name} (
                    {cols}
                )
            """)


@frozen
class View:
    name: str
    create_stmt: str
    column_names: list[str]

    async def create_if_not_exists(self, conn):
        stmt = f"""
        CREATE OR REPLACE VIEW {self.name} AS
        {self.create_stmt}
        """
        await conn.execute(stmt)


class StorageAbc(ABC):
    def __init__(self, backend):
        self.backend = backend

    async def close(self):
        await self.backend.close()

    @staticmethod
    async def create():
        raise NotImplementedError()

    async def exists_frontpage(self, name: str, dt: datetime):
        raise NotImplementedError()

    async def list_articles_on_frontpage(self, title_ids: list[int]):
        raise NotImplementedError()

    async def add_embedding(self, title_id: int, embedding):
        raise NotImplementedError()

    async def list_sites(self):
        raise NotImplementedError()

    async def list_neighbouring_main_articles(
        self,
        site_id: int,
        timestamp: datetime | None = None,
    ):
        raise NotImplementedError()

    async def add_page(self, collection, page, dt):
        raise NotImplementedError()
