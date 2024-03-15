import asyncio
from abc import ABC, abstractmethod
from attrs import frozen
import cattrs
from bs4 import BeautifulSoup
from yarl import URL

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot


cattrs.register_structure_hook(URL, lambda v, _: URL(v))


@frozen
class FeaturedArticle:
    url: URL

    @classmethod
    def from_internet_archive_url(cls, url_str: str) -> "FeaturedArticle":
        url = URL(url_str)
        original_str = url.path.split("/", 3)[-1]
        return cattrs.structure({"url": original_str}, cls)


@frozen
class FeaturedArticleSnapshot(ABC):
    title: str
    url: str
    original: FeaturedArticle

    @classmethod
    def create(cls, title, url):
        attrs = dict(
            title=title,
            url=url,
            original=FeaturedArticle.from_internet_archive_url(url),
        )
        return cls(**attrs)


@frozen
class TopArticle(ABC):
    article: FeaturedArticleSnapshot
    rank: int


@frozen
class MainArticle(ABC):
    article: FeaturedArticleSnapshot


@frozen
class MainPage(ABC):
    snapshot: InternetArchiveSnapshot
    soup: BeautifulSoup
    top_articles: list[TopArticle]
    main_article: MainArticle

    @staticmethod
    @abstractmethod
    def get_top_articles(soup: BeautifulSoup) -> list[TopArticle]:
        ...

    @staticmethod
    @abstractmethod
    def get_main_article(soup: BeautifulSoup) -> MainArticle:
        ...

    @classmethod
    async def from_snapshot(cls, snapshot: InternetArchiveSnapshot):
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, snapshot.text, "lxml")

        return cls(
            snapshot, soup, cls.get_top_articles(soup), cls.get_main_article(soup)
        )


@frozen
class ArchiveCollection:
    url: str
    MainPageClass: type[MainPage]
