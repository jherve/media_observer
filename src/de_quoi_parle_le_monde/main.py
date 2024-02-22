import requests
import requests_cache
from requests_cache.models.response import CachedResponse
from requests_cache.backends.sqlite import SQLiteCache
from bs4 import BeautifulSoup

http_session = requests_cache.CachedSession("ia",backend="sqlite")


class InternetArchive:
    # https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

    @staticmethod
    def search_snapshots(url: str, params: dict):
        return http_session.get("http://web.archive.org/cdx/search/cdx?", {"url": url} | {"filter": "statuscode:200"} | params)

    @staticmethod
    def parse_results(line: str):
        [
            id_,
            snap_date,
            url,
            mimetype,
            statuscode,
            hash_,
            size
        ] = line.split(" ")

        return snap_date, url

    @staticmethod
    def get_snapshot(url, snap_date):
        return http_session.get(f"http://web.archive.org/web/{snap_date}/{url}", headers={"lang": "fr"})


class WebPage:
    def __init__(self, doc):
        self.soup = BeautifulSoup(doc, 'html.parser')

    def get_top_articles_titles(self):
        return [s.text.strip() for s in w.soup.find_all("div", class_="top-article")]

def get_latest_snap():
    r = InternetArchive.search_snapshots("lemonde.fr", {"from": "20240222", "to": "20240222", "limit": 10})
    results = [InternetArchive.parse_results(r) for r in r.text.splitlines()]

    return InternetArchive.get_snapshot(*results[-1])


print(WebPage(get_latest_snap().text).get_top_articles_titles())

