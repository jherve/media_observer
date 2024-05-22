from de_quoi_parle_le_monde.article import (
    TopArticle,
    MainArticle,
    MainPage,
    to_text,
)


class BfmTvMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup):
        all_articles = soup.select("section[id*='top_contenus'] li > a")
        return [
            TopArticle.create(
                title=to_text(a, "h3"),
                url=a["href"],
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        def to_href(soup):
            link = soup.select("a")[0]
            return link["href"]

        [main] = soup.select("article.une_item")
        return MainArticle.create(
            title=to_text(main, "h2.title_une_item"),
            url=to_href(main),
        )
