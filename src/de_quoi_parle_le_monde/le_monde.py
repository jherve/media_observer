import asyncio
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot
from de_quoi_parle_le_monde.article import (
    FeaturedArticle,
    TopArticle,
    MainArticle,
    MainPage,
)


class LeMondeFeaturedArticle(FeaturedArticle):
    ...


class LeMondeMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.find_all("div", class_="top-article")
        return [
            TopArticle(
                article=LeMondeFeaturedArticle.create(
                    title=a.text.strip(), url=a.find("a")["href"]
                ),
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        main = soup.find("div", class_="article--main")
        return MainArticle(
            article=LeMondeFeaturedArticle.create(
                title=main.find("p", class_="article__title-label").text.strip(),
                url=main.find("a")["href"],
            )
        )

    @classmethod
    async def from_snapshot(
        cls, snapshot: InternetArchiveSnapshot
    ) -> "LeMondeMainPage":
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, snapshot.text, "lxml")
        return LeMondeMainPage(
            snapshot, soup, cls.get_top_articles(soup), cls.get_main_article(soup)
        )
