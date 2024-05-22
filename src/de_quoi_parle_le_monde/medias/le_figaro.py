from bs4 import BeautifulSoup

from de_quoi_parle_le_monde.article import (
    TopArticle,
    MainArticle,
    MainPage,
    to_text,
)


class LeFigaroMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup: BeautifulSoup):
        # Le Figaro does not have such a view on its frontpage

        return []

    @staticmethod
    def get_main_article(soup):
        main = soup.select(".fig-main .fig-ensemble__first-article")[0]
        url = main.select("a")[0]

        return MainArticle.create(
            title=to_text(main, ".fig-ensemble__title"),
            url=url["href"],
        )
