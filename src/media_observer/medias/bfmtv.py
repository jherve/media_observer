from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class BfmTvFrontPage(FrontPage):
    @classmethod
    def get_top_articles(cls, soup):
        all_articles = soup.select("section[id*='top_contenus'] li > a")
        return [
            TopArticle.create(
                title=a.select_unique("h3").stripped_text,
                url=a["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @classmethod
    def get_main_article(cls, soup):
        main = soup.select_unique("article.une_item")
        return MainArticle.create(
            title=main.select_unique("h2.title_une_item").stripped_text,
            url=main.select_first("a")["href"],
        )
