from attrs import frozen
from typing import ClassVar
import cattrs
import asyncio
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot
from de_quoi_parle_le_monde.article import TopArticle, MainArticle, MainPage

class LeMondeTopArticle(TopArticle):
    ...


class LeMondeMainArticle(MainArticle):
    ...


@frozen
class LeMondeMainPage(MainPage):
    snapshot: InternetArchiveSnapshot
    soup: BeautifulSoup

    def get_top_articles(self):
        all_articles = self.soup.find_all("div", class_="top-article")
        return [
            LeMondeTopArticle(title=a.text.strip(), url=a.find("a")["href"])
            for a in all_articles
        ]

    def main_article(self):
        main = self.soup.find("div", class_="article--main")
        return LeMondeMainArticle(
            title=main.find("p", class_="article__title-label").text.strip(),
            url=main.find("a")["href"],
        )

    @staticmethod
    async def from_snapshot(snapshot: InternetArchiveSnapshot) -> "LeMondeMainPage":
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, snapshot.text, "lxml")
        return LeMondeMainPage(snapshot, soup)


@frozen
class LeMondeArchive:
    url: ClassVar[str] = "https://lemonde.fr"
