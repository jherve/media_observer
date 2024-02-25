from attrs import frozen
import cattrs
from bs4 import BeautifulSoup

from internet_archive import InternetArchiveSnapshot


@frozen
class LeMondeTopArticle:
    title: str
    url: str

    @staticmethod
    def from_soup(soup: BeautifulSoup):
        return cattrs.structure(
            dict(title=soup.text.strip(), url=soup.find("a")["href"]), LeMondeTopArticle
        )


@frozen
class LeMondeMainArticle:
    title: str
    url: str

    @staticmethod
    def from_soup(soup: BeautifulSoup):
        attrs = dict(title=soup.find("h1").text.strip(), url=soup.find("a")["href"])
        return cattrs.structure(attrs, LeMondeMainArticle)


@frozen
class LeMondeMainPage:
    snapshot: InternetArchiveSnapshot
    soup: BeautifulSoup

    def get_top_articles(self):
        return [
            LeMondeTopArticle.from_soup(s)
            for s in self.soup.find_all("div", class_="top-article")
        ]

    def main_article(self):
        return LeMondeMainArticle.from_soup(
            self.soup.find("div", class_="article--main")
        )
