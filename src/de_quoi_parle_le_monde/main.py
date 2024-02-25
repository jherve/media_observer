from datetime import date, timedelta
import asyncio

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import InternetArchiveClient, CdxRequest
from de_quoi_parle_le_monde.le_monde import LeMondeMainPage


async def get_latest_snaps():
    dates = [date.today() - timedelta(days=n) for n in range(0, 10)]
    ia = InternetArchiveClient()

    def build_request(d):
        req = CdxRequest(
            url="lemonde.fr", from_=d, to_=d, limit=10, filter="statuscode:200"
        )
        return ia.search_snapshots(req)

    async def parse_snap(snap):
        soup = await ia.fetch_and_parse_snapshot(snap)
        return LeMondeMainPage(snap, soup)

    snaps = await asyncio.gather(*[build_request(d) for d in dates])
    top = await asyncio.gather(*[parse_snap(s[0]) for s in snaps])
    for t in top:
        print(t.get_top_articles()[0], t.main_article())


asyncio.run(get_latest_snaps())
