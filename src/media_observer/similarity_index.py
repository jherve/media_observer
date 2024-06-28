import asyncio
import os
from datetime import datetime
import pickle
from attrs import define, frozen
from typing import Any, Callable, ClassVar
from loguru import logger
from annoy import AnnoyIndex


from media_observer.storage import Storage
from media_observer.worker import Worker


file_path_index = "./similarity.index"
file_path_pickle_class = "./similarity.class"


@define
class SimilaritySearch:
    storage: Storage
    index: AnnoyIndex
    build_dt: datetime | None = None
    index_id_to_title: dict[int, int] = {}
    title_to_index_id: dict[int, int] = {}
    instance: ClassVar[Any | None] = None

    async def add_embeddings(self):
        embeds = await self.storage.list_all_embeddings()
        if not embeds:
            msg = (
                "Did not find any embeddings in storage. "
                "A plausible cause is that they have not been computed yet"
            )
            logger.error(msg)
            raise ValueError(msg)

        for idx, e in enumerate(embeds):
            self.index.add_item(idx, e["vector"])
            self.title_to_index_id[e["title_id"]] = idx
            self.index_id_to_title[idx] = e["title_id"]

        self.index.build(20)
        self.build_dt = datetime.now()

    async def search(
        self,
        title_ids: list[int],
        nb_results: int,
        score_func: Callable[[float], bool],
    ):
        try:
            [title_id] = [self.title_to_index_id[id] for id in title_ids]
        except KeyError as e:
            msg = (
                f"Could not find all embedding(s) in storage for {title_ids}. "
                "A plausible cause is that they have not been computed yet"
            )
            logger.error(msg)
            raise e

        indices, distances = self.index.get_nns_by_item(
            title_id, nb_results, include_distances=True
        )
        return [
            (
                title_id,
                [
                    (self.index_id_to_title[i], d)
                    for i, d in (zip(indices, distances))
                    if i != title_id and score_func(d)
                ],
            )
        ]

    @classmethod
    def create(cls, storage):
        d = 1024
        index = AnnoyIndex(d, "dot")
        return SimilaritySearch(storage, index)

    async def save(self):
        self.index.save(file_path_index)
        with open(file_path_pickle_class, "wb") as f:
            pickle.dump((self.index_id_to_title, self.title_to_index_id), f)

    @classmethod
    def _latest_index_file_modification_dt(cls) -> datetime:
        statinfo = os.stat(file_path_index)
        return datetime.fromtimestamp(statinfo.st_mtime)

    @property
    def stale(self) -> bool:
        return (
            self.build_dt is not None
            and self._latest_index_file_modification_dt() > self.build_dt
        )

    @classmethod
    def load(cls, storage):
        d = 1024
        index = AnnoyIndex(d, "dot")
        try:
            index.load(file_path_index)
            with open(file_path_pickle_class, "rb") as f:
                (index_to_title, title_to_index) = pickle.load(f)

            return SimilaritySearch(
                storage,
                index,
                cls._latest_index_file_modification_dt(),
                index_to_title,
                title_to_index,
            )
        except OSError:
            logger.warning("Could not find index data")
            return SimilaritySearch(storage, index)


@frozen
class SimilarityIndexWorker(Worker):
    storage: Storage
    new_embeddings_event: asyncio.Event

    async def run(self):
        while True:
            await self.new_embeddings_event.wait()

            sim_index = SimilaritySearch.create(self.storage)
            logger.info("Starting index..")
            await sim_index.add_embeddings()
            await sim_index.save()
            logger.info("Similarity index ready")

            self.new_embeddings_event.clear()
