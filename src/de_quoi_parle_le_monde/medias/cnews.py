import asyncio
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot
from de_quoi_parle_le_monde.article import (
    FeaturedArticleSnapshot,
    TopArticle,
    MainArticle,
    MainPage,
)


class CNewsFeaturedArticleSnapshot(FeaturedArticleSnapshot):
    ...


class CNewsMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.css.select(".top-news-content a")

        return [
            TopArticle(
                article=CNewsFeaturedArticleSnapshot.create(
                    title=a.find("h3", class_="dm-letop-title").text.strip(), url=a["href"]
                ),
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        main = soup.find("div", class_="dm-block-news_1_single_full")
        return MainArticle(
            article=CNewsFeaturedArticleSnapshot.create(
                title=main.find("h2", class_="dm-news-title").text.strip(),
                url=main.find("a")["href"],
            )
        )

    @classmethod
    async def from_snapshot(
        cls, snapshot: InternetArchiveSnapshot
    ) -> "CNewsMainPage":
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, snapshot.text, "lxml")

        return cls(
            snapshot, soup, cls.get_top_articles(soup), cls.get_main_article(soup)
        )
