from media_observer.article import (
    TopArticle,
    MainArticle,
    FrontPage,
)


class LeMondeFrontPage(FrontPage):
    @classmethod
    def get_top_articles(cls, soup):
        all_articles = soup.select("div.top-article")
        return [
            TopArticle.create(
                title=a.stripped_text,
                url=a.select_unique("a")["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @classmethod
    def get_main_article(cls, soup) -> MainArticle:
        if highlighted := cls._get_highlighted_article(soup):
            return highlighted
        else:
            return cls._get_non_highlighted_article(soup)

    @classmethod
    def _get_highlighted_article(cls, soup):
        try:
            main = soup.select_unique("div.hp-article-municipale")

            return MainArticle.create(
                title=main.select_unique("h2").stripped_text,
                url=main.select_first("a")["href"],
                is_highlighted=True,
            )
        except ValueError:
            return None

    @classmethod
    def _get_non_highlighted_article(cls, soup):
        main = soup.select_unique("div.article--main")
        return MainArticle.create(
            title=main.select_unique("p.article__title-label").stripped_text,
            url=main.select_first("a")["href"],
            is_highlighted=False,
        )
