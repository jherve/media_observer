import asyncio
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot
from de_quoi_parle_le_monde.article import (
    FeaturedArticle,
    TopArticle,
    MainArticle,
    MainPage,
)


class FranceTvInfoFeaturedArticle(FeaturedArticle):
    ...


class FranceTvInfoMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.find_all("article", class_="card-article-most-read")
        return [
            TopArticle(
                article=FranceTvInfoFeaturedArticle.create(
                    title=a.find(
                        "p", class_="card-article-most-read__title"
                    ).text.strip(),
                    url=a.find("a")["href"],
                ),
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        main = soup.find("article", class_="card-article-majeure") or soup.find(
            "article", class_="card-article-actu-forte"
        )
        title = main.find(class_="card-article-majeure__title") or main.find(
            class_="card-article-actu-forte__title"
        )

        return MainArticle(
            article=FranceTvInfoFeaturedArticle.create(
                title=title.text.strip(),
                url=main.find("a")["href"],
            )
        )

    @classmethod
    async def from_snapshot(
        cls, snapshot: InternetArchiveSnapshot
    ) -> "FranceTvInfoMainPage":
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, snapshot.text, "lxml")
        return FranceTvInfoMainPage(
            snapshot, soup, cls.get_top_articles(soup), cls.get_main_article(soup)
        )
