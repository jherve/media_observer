from bs4 import BeautifulSoup

from media_observer.article import (
    TopArticle,
    MainArticle,
    MainPage,
)


class Tf1InfoMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup: BeautifulSoup):
        all_articles = soup.select("#AllNews__List__0 .AllNewsItem .LinkArticle")

        return [
            Tf1InfoMainPage._get_top_article(a, idx)
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def _get_top_article(soup: BeautifulSoup, idx: int):
        [a] = soup.select("a")
        return TopArticle.create(
            title=a.text.strip(),
            url=a["href"],
            rank=idx + 1,
        )

    @staticmethod
    def get_main_article(soup):
        main = soup.select("#headlineid .ArticleCard__Title")[0]
        [url] = main.select("a")

        return MainArticle.create(
            title=url.text.strip(),
            url=url["href"],
        )
