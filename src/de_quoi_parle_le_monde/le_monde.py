from attrs import frozen
from typing import ClassVar
import cattrs
import asyncio
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot


@frozen
class LeMondeTopArticle:
    title: str
    url: str

    @staticmethod
    def from_soup(soup: BeautifulSoup):
        return cattrs.structure(
            dict(title=soup.text.strip(), url=soup.find("a")["href"]), LeMondeTopArticle
        )


@frozen
class LeMondeMainArticle:
    title: str
    url: str

    @staticmethod
    def from_soup(soup: BeautifulSoup):
        attrs = dict(
            title=soup.find("p", class_="article__title-label").text.strip(),
            url=soup.find("a")["href"],
        )
        return cattrs.structure(attrs, LeMondeMainArticle)


@frozen
class LeMondeMainPage:
    snapshot: InternetArchiveSnapshot
    soup: BeautifulSoup

    def get_top_articles(self):
        return [
            LeMondeTopArticle.from_soup(s)
            for s in self.soup.find_all("div", class_="top-article")
        ]

    def main_article(self):
        return LeMondeMainArticle.from_soup(
            self.soup.find("div", class_="article--main")
        )

    @staticmethod
    async def from_content(
        snapshot: InternetArchiveSnapshot, text: str
    ) -> "LeMondeMainPage":
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, text, "lxml")
        return LeMondeMainPage(snapshot, soup)


@frozen
class LeMondeArchive:
    url: ClassVar[str] = "https://lemonde.fr"
