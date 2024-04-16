from typing import Callable
from loguru import logger
import faiss
import numpy as np


class SimilaritySearch:
    instance = None

    def __init__(self, storage) -> None:
        d = 1024
        self.storage = storage
        self.index = faiss.index_factory(d, "IDMap,Flat", faiss.METRIC_INNER_PRODUCT)

    async def add_embeddings(self):
        embeds = await self.storage.list_all_articles_embeddings()
        if not embeds:
            msg = (
                f"Did not find any embeddings in storage. "
                "A plausible cause is that they have not been computed yet"
            )
            logger.error(msg)
            raise ValueError(msg)

        all_titles = np.array([e["title_embedding"] for e in embeds])
        faiss.normalize_L2(all_titles)
        self.index.add_with_ids(
            all_titles, [e["featured_article_snapshot_id"] for e in embeds]
        )

    async def search(
        self,
        featured_article_snapshot_ids: list[int],
        nb_results: int,
        score_func: Callable[[float], bool],
    ):
        embeds = await self.storage.get_article_embedding(featured_article_snapshot_ids)

        if (nb_embeds := len(embeds)) != (
            nb_articles := len(featured_article_snapshot_ids)
        ):
            msg = (
                f"Expected {nb_articles} embedding(s) in storage but found only {nb_embeds}. "
                "A plausible cause is that they have not been computed yet"
            )
            logger.error(msg)
            raise ValueError(msg)

        all_titles = np.array([e["title_embedding"] for e in embeds])
        faiss.normalize_L2(all_titles)
        D, I = self.index.search(np.array(all_titles), nb_results)

        return [
            (
                featured_article_snapshot_ids[idx],
                [(int(i), d) for d, i in res if score_func(d)],
            )
            for idx, res in enumerate(np.dstack((D, I)))
        ]

    @classmethod
    def create(cls, storage):
        if cls.instance is None:
            cls.instance = SimilaritySearch(storage)

        return cls.instance
