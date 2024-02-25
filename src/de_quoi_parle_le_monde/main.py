from datetime import date, timedelta
import asyncio

from de_quoi_parle_le_monde.http import HttpClient
from de_quoi_parle_le_monde.internet_archive import InternetArchiveClient, CdxRequest
from de_quoi_parle_le_monde.le_monde import LeMondeMainPage


async def get_latest_snaps():
    dates = [date.today() - timedelta(days=n) for n in range(0, 10)]
    ia = InternetArchiveClient()

    async def req_and_parse_first_snap(date):
        req = CdxRequest(
            url="lemonde.fr", from_=date, to_=date, limit=10, filter="statuscode:200"
        )
        snaps = await ia.search_snapshots(req)
        snap = snaps[0]
        soup = await ia.fetch_and_parse_snapshot(snap)
        return LeMondeMainPage(snap, soup)

    top = await asyncio.gather(*[req_and_parse_first_snap(d) for d in dates])
    for t in top:
        print(t.get_top_articles()[0], t.main_article())


asyncio.run(get_latest_snaps())
