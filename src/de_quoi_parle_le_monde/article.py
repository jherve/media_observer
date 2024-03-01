from abc import ABC, abstractmethod
from attrs import frozen
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot


@frozen
class TopArticle(ABC):
    title: str
    url: str
    rank: int


@frozen
class MainArticle(ABC):
    title: str
    url: str


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
