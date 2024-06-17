from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class FranceTvInfoFrontPage(FrontPage):
    @classmethod
    def get_top_articles(cls, soup):
        all_articles = soup.select("article.card-article-most-read")

        return [
            TopArticle.create(
                title=a.select_unique("p.card-article-most-read__title").stripped_text,
                url=a.select_unique("a")["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @classmethod
    def get_main_article(cls, soup):
        try:
            return FranceTvInfoFrontPage._get_highlighted_article(soup)
        except ValueError:
            return FranceTvInfoFrontPage._get_non_highlighted_article(soup)

    @staticmethod
    def _get_highlighted_article(soup):
        main = soup.select_unique("article.card-article-actu-forte")
        title = main.select_unique(".card-article-actu-forte__title")

        return MainArticle.create(
            title=title.stripped_text,
            url=main.select_unique("a")["href"],
            is_highlighted=True,
        )

    @staticmethod
    def _get_non_highlighted_article(soup):
        main = soup.select_unique("article.card-article-majeure")
        title = main.select_unique(".card-article-majeure__title")

        return MainArticle.create(
            title=title.stripped_text,
            url=main.select_unique("a")["href"],
            is_highlighted=False,
        )
