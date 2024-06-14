from bs4 import BeautifulSoup

from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class Tf1InfoFrontPage(FrontPage):
    @staticmethod
    def get_top_articles(soup: BeautifulSoup):
        all_articles = soup.select("#AllNews__List__0 .AllNewsItem .LinkArticle")

        return [
            Tf1InfoFrontPage._get_top_article(a, idx)
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def _get_top_article(soup: BeautifulSoup, idx: int):
        a = soup.select_unique("a")
        return TopArticle.create(
            title=a.stripped_text,
            url=a["href"],
            rank=idx + 1,
        )

    @staticmethod
    def get_main_article(soup):
        main = soup.select_first("#headlineid .ArticleCard__Title")
        url = main.select_unique("a")

        return MainArticle.create(
            title=url.stripped_text,
            url=url["href"],
        )
