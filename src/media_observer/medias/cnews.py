from bs4 import BeautifulSoup

from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class CNewsFrontPage(FrontPage):
    @classmethod
    def get_top_articles(cls, soup: BeautifulSoup):
        all_articles = soup.select(".top-news-content a")

        return [
            TopArticle.create(
                title=a.select_unique("h3.dm-letop-title").stripped_text,
                url=a["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @classmethod
    def get_main_article(cls, soup):
        main = soup.select_first("div.dm-block")
        url = main.select_unique("a")

        return MainArticle.create(
            title=main.select_unique("h2.dm-news-title").stripped_text,
            url=url["href"],
        )
