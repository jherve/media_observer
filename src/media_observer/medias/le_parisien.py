from bs4 import BeautifulSoup

from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class LeParisienFrontPage(FrontPage):
    @classmethod
    def get_top_articles(cls, soup: BeautifulSoup):
        all_articles = soup.select("a[data-block-name='Les_plus_lus']")

        return [
            TopArticle.create(
                title=a.stripped_text,
                url=a["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @classmethod
    def get_main_article(cls, soup):
        main = soup.select_first(".homepage__top article")
        url = main.select_first("a")

        return MainArticle.create(
            title=url.stripped_text,
            url=url["href"],
        )
