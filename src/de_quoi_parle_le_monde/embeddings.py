import asyncio
from loguru import logger
from itertools import islice
from collections import defaultdict
from typing import Any
from attrs import frozen
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from de_quoi_parle_le_monde.storage import Storage


def batched(iterable, n):
    """
    Batch data into tuples of length n. The last batch may be shorter.
        `batched('ABCDEFG', 3) --> ABC DEF G`

    Straight from : https://docs.python.org/3.11/library/itertools.html#itertools-recipes
    """
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


@frozen
class EmbeddingsJob:
    article_id: int
    text: NDArray

    @staticmethod
    async def create(storage: Storage):
        all_snapshots = await storage.list_all_featured_article_snapshots()
        all_embeds_ids = set(
            await storage.list_all_embedded_featured_article_snapshot_ids()
        )

        all_snapshots_not_stored = (
            s for s in all_snapshots if s["id"] not in all_embeds_ids
        )

        return [EmbeddingsJob(s["id"], s["title"]) for s in all_snapshots_not_stored]


@frozen
class EmbeddingsWorker:
    storage: Storage
    model: Any

    def compute_embeddings_for(self, sentences: dict[int, str]):
        logger.debug(f"Computing embeddings for {len(sentences)} sentences")
        inverted_dict = defaultdict(list)
        for idx, (k, v) in enumerate(list(sentences.items())):
            inverted_dict[v].append((idx, k))
        all_texts = list(inverted_dict.keys())
        all_embeddings = self.model.encode(all_texts)

        embeddings_by_id = {}
        for e, text in zip(all_embeddings, all_texts):
            all_ids = [id for (_, id) in inverted_dict[text]]
            for i in all_ids:
                embeddings_by_id[i] = e

        return embeddings_by_id

    async def store_embeddings(self, embeddings_by_id: dict):
        logger.debug(f"Storing {len(embeddings_by_id)} embeddings")
        for i, embed in embeddings_by_id.items():
            await self.storage.add_embedding(i, embed)

    async def run(self, jobs: list[EmbeddingsJob]):
        batch_size = 64
        for batch in batched(jobs, batch_size):
            embeddings_by_id = self.compute_embeddings_for(
                {j.article_id: j.text for j in batch}
            )
            await self.store_embeddings(embeddings_by_id)

    @staticmethod
    def create(storage, model_path):
        model = SentenceTransformer(model_path)
        return EmbeddingsWorker(storage, model)


async def main():
    storage = await Storage.create()

    logger.info("Starting embeddings service..")
    jobs = await EmbeddingsJob.create(storage)
    if jobs:
        loop = asyncio.get_event_loop()
        worker = await loop.run_in_executor(
            None,
            EmbeddingsWorker.create,
            storage,
            "dangvantuan/sentence-camembert-large",
        )
        await worker.run(jobs)

    logger.info("Embeddings service exiting")


if __name__ == "__main__":
    asyncio.run(main())
