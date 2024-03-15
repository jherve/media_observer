import asyncio
from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot
from de_quoi_parle_le_monde.article import (
    FeaturedArticleSnapshot,
    TopArticle,
    MainArticle,
    MainPage,
)


class FranceTvInfoFeaturedArticleSnapshot(FeaturedArticleSnapshot):
    ...


class FranceTvInfoMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.find_all("article", class_="card-article-most-read")
        return [
            TopArticle(
                article=FranceTvInfoFeaturedArticleSnapshot.create(
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
            article=FranceTvInfoFeaturedArticleSnapshot.create(
                title=title.text.strip(),
                url=main.find("a")["href"],
            )
        )
