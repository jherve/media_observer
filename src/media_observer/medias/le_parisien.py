from bs4 import BeautifulSoup

from media_observer.article import (
    TopArticle,
    MainArticle,
    MainPage,
)


class LeParisienMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup: BeautifulSoup):
        all_articles = soup.select("a[data-block-name='Les_plus_lus']")

        return [
            TopArticle.create(
                title=a.text.strip(),
                url=a["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        main = soup.select(".homepage__top article")[0]
        url = main.select("a")[0]

        return MainArticle.create(
            title=url.text.strip(),
            url=url["href"],
        )
