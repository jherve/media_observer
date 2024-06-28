import asyncio
import concurrent.futures
from itertools import islice
from typing import Any
from loguru import logger
from attrs import define, field

from media_observer.worker import Worker
from media_observer.storage import Storage


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


@define
class EmbeddingsWorker(Worker):
    storage: Storage
    model_name: str
    batch_size: int
    new_embeddings_event: asyncio.Event
    model: Any = field(init=False, default=None)

    async def run(self):
        def load_model():
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)

        while True:
            loop = asyncio.get_running_loop()
            if self.model is None:
                await loop.run_in_executor(None, load_model)

            all_titles = [
                (t["id"], t["text"])
                for t in await self.storage.list_all_titles_without_embedding()
            ]

            for batch in batched(all_titles, self.batch_size):
                with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
                    embeddings = await loop.run_in_executor(
                        pool, self.compute_embeddings_for, self.model, batch
                    )
                for i, embed in embeddings.items():
                    await self.storage.add_embedding(i, embed)

                logger.debug(f"Stored {len(embeddings)} embeddings")

                if embeddings:
                    self.new_embeddings_event.set()

            await asyncio.sleep(5)

    @staticmethod
    def compute_embeddings_for(model: Any, sentences: tuple[tuple[int, str]]):
        logger.debug(f"Computing embeddings for {len(sentences)} sentences")
        all_texts = [t[1] for t in sentences]
        all_embeddings = model.encode(all_texts)

        return {sentences[idx][0]: e for idx, e in enumerate(all_embeddings)}
