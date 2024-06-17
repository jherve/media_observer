from bs4 import BeautifulSoup

from media_observer.article import (
    MainArticle,
    FrontPage,
)


class LeFigaroFrontPage(FrontPage):
    @classmethod
    def get_top_articles(cls, soup: BeautifulSoup):
        # Le Figaro does not have such a view on its frontpage

        return []

    @classmethod
    def get_main_article(cls, soup):
        main = soup.select_first(".fig-main .fig-ensemble__first-article")
        url = main.select_first("a")

        return MainArticle.create(
            title=main.select_unique(".fig-ensemble__title").stripped_text,
            url=url["href"],
        )
