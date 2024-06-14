from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class FranceTvInfoFrontPage(FrontPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.select("article.card-article-most-read")

        return [
            TopArticle.create(
                title=a.select_unique("p.card-article-most-read__title").stripped_text,
                url=a.select_unique("a")["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        def get_kwargs(main_selector, title_selector):
            main = soup.select_unique(main_selector)
            title = main.select_unique(title_selector)
            return dict(title=title.stripped_text, url=main.select_unique("a")["href"])

        try:
            kwargs = get_kwargs(
                "article.card-article-majeure", ".card-article-majeure__title"
            )
        except ValueError:
            kwargs = get_kwargs(
                "article.card-article-actu-forte", ".card-article-actu-forte__title"
            )

        return MainArticle.create(**kwargs)
