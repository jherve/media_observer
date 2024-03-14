from de_quoi_parle_le_monde.article import ArchiveCollection

from .france_tv_info import FranceTvInfoMainPage
from .le_monde import LeMondeMainPage


media_collection = {
    "france_tv_info": ArchiveCollection(
        url="https://francetvinfo.fr", MainPageClass=FranceTvInfoMainPage
    ),
    "le_monde": ArchiveCollection(
        url="https://lemonde.fr", MainPageClass=LeMondeMainPage
    ),
}
