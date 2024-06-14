from bs4 import BeautifulSoup

from media_observer.article import (
    MainArticle,
    FrontPage,
)


class LeFigaroFrontPage(FrontPage):
    @staticmethod
    def get_top_articles(soup: BeautifulSoup):
        # Le Figaro does not have such a view on its frontpage

        return []

    @staticmethod
    def get_main_article(soup):
        main = soup.select_first(".fig-main .fig-ensemble__first-article")
        url = main.select_first("a")

        return MainArticle.create(
            title=main.select_unique(".fig-ensemble__title").stripped_text,
            url=url["href"],
        )
