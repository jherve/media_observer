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
        highlighted = cls._get_kwargs(soup, ".megamax article.une_item")
        if highlighted is not None:
            return highlighted
        else:
            return cls._get_kwargs(soup, ".block_une article.une_item")

    @classmethod
    def _get_kwargs(cls, soup, main_selector: str):
        try:
            main = soup.select_unique(main_selector)
            return MainArticle.create(
                title=main.select_unique("h2").stripped_text,
                url=main.select_first("a")["href"],
            )
        except ValueError:
            return None
