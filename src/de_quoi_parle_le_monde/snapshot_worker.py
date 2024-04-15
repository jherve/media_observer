from datetime import date, datetime, time, timedelta
import asyncio
from attrs import frozen
import traceback
from loguru import logger
from sentence_transformers import SentenceTransformer

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import (
    InternetArchiveClient,
    SnapshotNotYetAvailable,
)
from de_quoi_parle_le_monde.medias import media_collection
from de_quoi_parle_le_monde.storage import Storage

from itertools import islice
from collections import defaultdict


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
class SnapshotWorker:
    storage: Storage
    ia_client: InternetArchiveClient

    @staticmethod
    def last_n_days_at_hours(n: int, hours: list[int]) -> list[datetime]:
        return [
            datetime.combine(date.today() - timedelta(days=i), time(hour=h))
            for i in range(0, n)
            for h in hours
        ]

    async def find(self, collection, dt):
        try:
            return await self.ia_client.get_snapshot_id_closest_to(collection.url, dt)
        except SnapshotNotYetAvailable as e:
            logger.warning(f"Snapshot for {collection.name} @ {dt} not yet available")
            raise e
        except Exception as e:
            logger.error(
                f"Error while trying to find snapshot for {collection.name} @ {dt}"
            )
            traceback.print_exception(e)
            raise e

    async def fetch(self, snap_id):
        try:
            return await self.ia_client.fetch(snap_id)
        except Exception as e:
            logger.error(f"Error while fetching {snap_id}")
            traceback.print_exception(e)
            raise e

    async def parse(self, collection, snapshot):
        try:
            return await collection.MainPageClass.from_snapshot(snapshot)
        except Exception as e:
            logger.error(f"Error while parsing {snapshot}")
            traceback.print_exception(e)
            raise e

    async def store(self, page, collection, dt):
        try:
            site_id = await self.storage.add_site(collection.name, collection.url)
            snapshot_id = await self.storage.add_snapshot(site_id, page.snapshot.id, dt)

            article_id = await self.storage.add_featured_article(
                page.main_article.article.original
            )
            main_article_snap_id = await self.storage.add_featured_article_snapshot(
                article_id, page.main_article.article
            )
            await self.storage.add_main_article(snapshot_id, main_article_snap_id)

            for t in page.top_articles:
                article_id = await self.storage.add_featured_article(t.article.original)
                top_article_snap_id = await self.storage.add_featured_article_snapshot(
                    article_id, t.article
                )
                await self.storage.add_top_article(snapshot_id, top_article_snap_id, t)

        except Exception as e:
            logger.error(
                f"Error while attempting to store {page} from {collection.name} @ {dt}"
            )
            traceback.print_exception(e)
            raise e

    async def handle_snap(self, collection, dt):
        try:
            logger.info(f"Start handling snap for collection {collection.name} @ {dt}")
            id_closest = await self.find(collection, dt)
            closest = await self.ia_client.fetch(id_closest)
            main_page = await self.parse(collection, closest)
            await self.store(main_page, collection, dt)
            logger.info(f"Snap for collection {collection.name} @ {dt} is stored")
        except Exception as e:
            return


async def download_all(
    http_client: HttpClient, storage: Storage, n_days: int, hours: list[int]
):
    dts = SnapshotWorker.last_n_days_at_hours(n_days, hours)

    async with http_client.session() as session:
        ia = InternetArchiveClient(session)
        worker = SnapshotWorker(storage, ia)

        return await asyncio.gather(
            *[worker.handle_snap(c, d) for d in dts for c in media_collection.values()]
        )


@frozen
class EmbeddingsWorker:
    storage: Storage
    model: SentenceTransformer

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

    @staticmethod
    def create(storage, model_path):
        model = SentenceTransformer(model_path)
        return EmbeddingsWorker(storage, model)


async def compute_embeddings(storage: Storage):
    worker = EmbeddingsWorker.create(storage, "dangvantuan/sentence-camembert-large")
    all_snapshots = await storage.list_all_featured_article_snapshots()

    batch_size = 64
    for batch in batched(all_snapshots, batch_size):
        embeddings_by_id = worker.compute_embeddings_for(
            {s["id"]: s["title"] for s in batch}
        )
        await worker.store_embeddings(embeddings_by_id)

    return worker
