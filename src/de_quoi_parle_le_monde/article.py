from abc import ABC, abstractmethod
from attrs import frozen
import cattrs
from bs4 import BeautifulSoup
from yarl import URL

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot


cattrs.register_structure_hook(URL, lambda v, _: URL(v))


@frozen
class FeaturedArticleSnapshot(ABC):
    title: str
    url: str
    original: URL

    @staticmethod
    def to_original_url(url: str) -> URL:
        url = URL(url)
        original_str = url.path.split("/", 3)[-1]
        original = URL(original_str)
        assert original.is_absolute(), f"{original}"
        return original

    @classmethod
    def create(cls, title, url):
        attrs = dict(title=title, url=url, original=cls.to_original_url(url))
        return cattrs.structure(attrs, cls)


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

    @classmethod
    @abstractmethod
    async def from_snapshot(cls, snapshot: InternetArchiveSnapshot):
        ...


@frozen
class ArchiveCollection:
    url: str
    MainPageClass: type[MainPage]
