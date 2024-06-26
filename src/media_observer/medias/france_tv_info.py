from media_observer.article import (
    TopArticle,
    MainArticle,
    MainPage,
    to_text,
)


class FranceTvInfoMainPage(MainPage):
    @staticmethod
    def get_top_articles(soup):
        def to_href(article, selector):
            [url] = article.select(selector)
            return url["href"]

        all_articles = soup.select("article.card-article-most-read")

        return [
            TopArticle.create(
                title=to_text(a, "p.card-article-most-read__title"),
                url=to_href(a, "a"),
                rank=idx + 1,
            )
            for idx, a in enumerate(all_articles)
        ]

    @staticmethod
    def get_main_article(soup):
        def select_first_of(soup, *selectors):
            for s in selectors:
                if found := soup.select(s):
                    return found
            return None

        [main] = select_first_of(
            soup, "article.card-article-majeure", "article.card-article-actu-forte"
        )
        [title] = select_first_of(
            main, ".card-article-majeure__title", ".card-article-actu-forte__title"
        )

        return MainArticle.create(
            title=title.text.strip(),
            url=main.find("a")["href"],
        )
