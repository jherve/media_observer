from bs4 import BeautifulSoup

from media_observer.article import (
    TopArticle,
    MainArticle,
    MainPage,
    to_text,
)


class CNewsMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup: BeautifulSoup):
        all_articles = soup.select(".top-news-content a")

        return [
            TopArticle.create(
                title=to_text(a, "h3.dm-letop-title"),
                url=a["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        main = soup.select("div.dm-block")[0]
        [url] = main.select("a")

        return MainArticle.create(
            title=to_text(main, "h2.dm-news-title"),
            url=url["href"],
        )
