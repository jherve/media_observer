from de_quoi_parle_le_monde.article import ArchiveCollection

from .france_tv_info import FranceTvInfoMainPage
from .le_monde import LeMondeMainPage
from .cnews import CNewsMainPage
from .bfmtv import BfmTvMainPage


media_collection = {
    c.name: c
    for c in [
        ArchiveCollection(
            name="france_tv_info",
            url="https://francetvinfo.fr",
            MainPageClass=FranceTvInfoMainPage,
        ),
        ArchiveCollection(
            name="le_monde", url="https://lemonde.fr", MainPageClass=LeMondeMainPage
        ),
        ArchiveCollection(
            name="cnews", url="https://cnews.fr", MainPageClass=CNewsMainPage
        ),
        ArchiveCollection(
            name="bfmtv", url="https://bfmtv.com", MainPageClass=BfmTvMainPage
        ),
    ]
}
