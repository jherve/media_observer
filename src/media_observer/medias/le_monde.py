from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
    to_text,
)


class LeMondeFrontPage(FrontPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.select("div.top-article")
        return [
            TopArticle.create(
                title=a.text.strip(),
                url=a.find("a")["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        def to_href(soup):
            link = soup.select("a")[0]
            return link["href"]

        [main] = soup.select("div.article--main")
        return MainArticle.create(
            title=to_text(main, "p.article__title-label"),
            url=to_href(main),
        )
