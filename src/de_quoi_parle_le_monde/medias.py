from de_quoi_parle_le_monde.article import ArchiveCollection

from de_quoi_parle_le_monde.france_tv_info import FranceTvInfoMainPage
from de_quoi_parle_le_monde.le_monde import LeMondeMainPage


media_collection = {
    "france_tv_info": ArchiveCollection(
        url="https://francetvinfo.fr", MainPageClass=FranceTvInfoMainPage
    ),
    "le_monde": ArchiveCollection(
        url="https://lemonde.fr", MainPageClass=LeMondeMainPage
    ),
}
