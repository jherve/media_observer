import asyncio
from abc import ABC, abstractmethod
from attrs import frozen, field, validators
import cattrs
from bs4 import BeautifulSoup
from yarl import URL

from de_quoi_parle_le_monde.internet_archive import InternetArchiveSnapshot


cattrs.register_structure_hook(URL, lambda v, _: URL(v))


def url_is_absolute(instance, attribute, value: URL):
    if not value.is_absolute():
        raise ValueError(f"Expected absolute URL, got {value}")


def url_has_scheme(instance, attribute, value: URL):
    if len(value.scheme) == 0:
        raise ValueError(f"Expected a scheme in URL, got {value}")


@frozen
class FeaturedArticle:
    url: URL = field(validator=[url_is_absolute, url_has_scheme])


@frozen
class FeaturedArticleSnapshot(ABC):
    title: str = field(validator=validators.min_len(1))
    url: URL = field(validator=[url_is_absolute, url_has_scheme])
    original: FeaturedArticle

    @classmethod
    def create(cls, title, url):
        absolute = cls.clean_web_archive_url(url)
        attrs = dict(
            title=title,
            url=absolute,
            original={"url": cls.extract_url_from_web_archive(absolute)},
        )
        return cattrs.structure(attrs, cls)

    @staticmethod
    def extract_url_from_web_archive(url: URL):
        # This extract e.g. this URL
        # https://www.lemonde.fr/economie/article/2024/05/22/totalenergies-cent-bougies-et-un-feu-de-critiques_6234759_3234.html
        # from an URL that looks like :
        # http://web.archive.org/web/20240522114811/https://www.lemonde.fr/economie/article/2024/05/22/totalenergies-cent-bougies-et-un-feu-de-critiques_6234759_3234.html
        return url.path.split("/", 3)[-1]

    @staticmethod
    def clean_web_archive_url(url_str: str):
        parsed = URL(url_str)

        if not parsed.is_absolute():
            base = URL("https://web.archive.org")
            return base.join(parsed)
        elif len(parsed.scheme) == 0:
            return parsed.with_scheme("https")
        else:
            return parsed


@frozen
class TopArticle(ABC):
    article: FeaturedArticleSnapshot
    rank: int

    @classmethod
    def create(cls, title, url, rank):
        article = FeaturedArticleSnapshot.create(title, url)
        attrs = {"article": cattrs.unstructure(article), "rank": rank}
        return cattrs.structure(attrs, cls)


@frozen
class MainArticle(ABC):
    article: FeaturedArticleSnapshot

    @classmethod
    def create(cls, title, url):
        article = FeaturedArticleSnapshot.create(title, url)
        return cls(article)


@frozen
class MainPage(ABC):
    snapshot: InternetArchiveSnapshot
    soup: BeautifulSoup = field(repr=False)
    top_articles: list[TopArticle]
    main_article: MainArticle

    @staticmethod
    @abstractmethod
    def get_top_articles(soup: BeautifulSoup) -> list[TopArticle]: ...

    @staticmethod
    @abstractmethod
    def get_main_article(soup: BeautifulSoup) -> MainArticle: ...

    @classmethod
    async def from_snapshot(cls, snapshot: InternetArchiveSnapshot):
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, snapshot.text, "lxml")

        return cls(
            snapshot, soup, cls.get_top_articles(soup), cls.get_main_article(soup)
        )


@frozen
class ArchiveCollection:
    name: str
    url: str
    MainPageClass: type[MainPage]
    logo_background_color: str
    logo_src: str | None = None
    logo_content: str | None = None


def to_text(soup: BeautifulSoup, selector: str) -> str:
    [text_element] = soup.select(selector)
    return text_element.text.strip()
