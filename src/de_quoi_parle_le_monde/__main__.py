import requests
import requests_cache
from requests_cache.models.response import CachedResponse
from requests_cache.backends.sqlite import SQLiteCache

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
        return http_session.get(f"http://web.archive.org/web/{snap_date}/{url}")

r = InternetArchive.search_snapshots("lemonde.fr", {"from": "20240222", "to": "20240222", "limit": 10})

results = [InternetArchive.parse_results(r) for r in r.text.splitlines()]

print(InternetArchive.get_snapshot(*results[0]))
