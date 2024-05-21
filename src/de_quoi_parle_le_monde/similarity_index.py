import asyncio
import pickle
from attrs import define
from typing import Any, Callable, ClassVar
from loguru import logger
from annoy import AnnoyIndex


from de_quoi_parle_le_monde.storage import Storage


file_path_index = "./similarity.index"
file_path_pickle_class = "./similarity.class"



@define
class SimilaritySearch:
    storage: Storage
    index: AnnoyIndex
    embedding_to_featured: dict[int, int] = {}
    featured_to_embedding: dict[int, int] = {}
    instance: ClassVar[Any | None] = None

    async def add_embeddings(self):
        embeds = await self.storage.list_all_articles_embeddings()
        if not embeds:
            msg = (
                "Did not find any embeddings in storage. "
                "A plausible cause is that they have not been computed yet"
            )
            logger.error(msg)
            raise ValueError(msg)

        for e in embeds:
            self.index.add_item(e["id"], e["title_embedding"])
            self.embedding_to_featured[e["id"]] = e["featured_article_snapshot_id"]
            self.featured_to_embedding[e["featured_article_snapshot_id"]] = e["id"]

        self.index.build(20)

    async def search(
        self,
        featured_article_snapshot_ids: list[int],
        nb_results: int,
        score_func: Callable[[float], bool],
    ):
        try:
            [embed_id] = [
                self.featured_to_embedding[id_] for id_ in featured_article_snapshot_ids
            ]
        except KeyError as e:
            msg = (
                f"Could not find all embedding(s) in storage for {featured_article_snapshot_ids}. "
                "A plausible cause is that they have not been computed yet"
            )
            logger.error(msg)
            raise e

        indices, distances = self.index.get_nns_by_item(
            embed_id, nb_results, include_distances=True
        )
        return [
            (
                embed_id,
                [
                    (self.embedding_to_featured[i], d)
                    for i, d in (zip(indices, distances))
                    if i != embed_id and score_func(d)
                ],
            )
        ]

    @classmethod
    def create(cls, storage):
        if cls.instance is None:
            d = 1024
            index = AnnoyIndex(d, "dot")
            cls.instance = SimilaritySearch(storage, index)

        return cls.instance

    async def save(self):
        self.index.save(file_path_index)
        with open(file_path_pickle_class, "wb") as f:
            pickle.dump((self.embedding_to_featured, self.featured_to_embedding), f)

    @classmethod
    def load(cls, storage):
        if cls.instance is None:
            d = 1024
            index = AnnoyIndex(d, "dot")
            index.load(file_path_index)
            with open(file_path_pickle_class, "rb") as f:
                (embedding_to_featured, featured_to_embedding) = pickle.load(f)

            cls.instance = SimilaritySearch(storage, index, embedding_to_featured, featured_to_embedding)

        return cls.instance


async def main():
    storage = await Storage.create()
    sim_index = SimilaritySearch.create(storage)

    logger.info("Starting index..")
    await sim_index.add_embeddings()
    await sim_index.save()
    logger.info("Similarity index ready")


if __name__ == "__main__":
    asyncio.run(main())
