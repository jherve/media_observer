import asyncio
from abc import ABC, abstractmethod
from attrs import frozen, field, validators
import cattrs
from bs4 import BeautifulSoup, ResultSet
from yarl import URL
from zoneinfo import ZoneInfo

from media_observer.internet_archive import InternetArchiveSnapshot


def structure_str(s, _):
    if not isinstance(s, str):
        raise ValueError(f"Expected str, got {s}")
    return s


cattrs.register_structure_hook(URL, lambda v, _: URL(v))
# Oddly enough an extra check is required so ensure that str values are not None
# https://github.com/python-attrs/cattrs/issues/26#issuecomment-358594015
cattrs.register_structure_hook(str, structure_str)


def url_is_absolute(instance, attribute, value: URL):
    if not value.is_absolute():
        raise ValueError(f"Expected absolute URL, got {value}")


def url_has_scheme(instance, attribute, value: URL):
    if len(value.scheme) == 0:
        raise ValueError(f"Expected a scheme in URL, got {value}")


@frozen
class Article:
    url: URL = field(validator=[url_is_absolute, url_has_scheme])


@frozen
class ArticleSnapshot(ABC):
    title: str = field(validator=validators.min_len(1))
    url: URL = field(validator=[url_is_absolute, url_has_scheme])
    original: Article

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
    article: ArticleSnapshot
    rank: int

    @classmethod
    def create(cls, title, url, rank):
        article = ArticleSnapshot.create(title, url)
        attrs = {"article": cattrs.unstructure(article), "rank": rank}
        return cattrs.structure(attrs, cls)


@frozen
class MainArticle(ABC):
    article: ArticleSnapshot
    is_live: bool | None
    is_highlighted: bool | None

    @classmethod
    def create(cls, title, url, *, is_live=None, is_highlighted=None):
        article = ArticleSnapshot.create(title, url)
        return cls(article, is_live, is_highlighted)


class MagnificentSoup(BeautifulSoup):
    def select(self, *args, **kwargs):
        def to_magnificient(soup):
            soup.__class__ = MagnificentSoup
            return soup

        return ResultSet(
            None, [to_magnificient(s) for s in super().select(*args, **kwargs)]
        )

    def select_first(self, selector: str) -> "MagnificentSoup":
        try:
            soup = self.select(selector)[0]
            soup.__class__ = MagnificentSoup
            return soup
        except IndexError:
            raise ValueError(f"Could not find {selector}")

    def select_unique(self, selector: str) -> "MagnificentSoup":
        match self.select(selector):
            case [soup]:
                soup.__class__ = MagnificentSoup
                return soup

            case many_or_zero:
                raise ValueError(
                    f"Expected a unique element matching {selector}, found {len(many_or_zero)}"
                )

    @property
    def stripped_text(self) -> str:
        return self.text.strip()


@frozen
class FrontPage(ABC):
    snapshot: InternetArchiveSnapshot
    soup: MagnificentSoup = field(repr=False)
    top_articles: list[TopArticle]
    main_article: MainArticle

    @classmethod
    @abstractmethod
    def get_top_articles(cls, soup: MagnificentSoup) -> list[TopArticle]: ...

    @classmethod
    @abstractmethod
    def get_main_article(cls, soup: MagnificentSoup) -> MainArticle: ...

    @classmethod
    async def from_snapshot(cls, snapshot: InternetArchiveSnapshot):
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, MagnificentSoup, snapshot.text, "lxml")

        return cls(
            snapshot, soup, cls.get_top_articles(soup), cls.get_main_article(soup)
        )


@frozen
class ArchiveCollection:
    name: str
    url: str
    tz: ZoneInfo
    FrontPageClass: type[FrontPage]
    logo_background_color: str
    logo_src: str | None = None
    logo_content: str | None = None


def to_text(soup: BeautifulSoup, selector: str) -> str:
    [text_element] = soup.select(selector)
    return text_element.text.strip()
