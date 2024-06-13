from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from babel.dates import format_datetime
from babel import Locale
import humanize
from zoneinfo import ZoneInfo

from media_observer.medias import media_collection
from media_observer.storage import Storage
from media_observer.similarity_index import SimilaritySearch


def add_date_processing(_any):
    # At the moment this information comes out of nowhere but one might imagine that
    # in the future it can be deducted from the request or from information the
    # user gives.
    user_tz = ZoneInfo("Europe/Paris")

    def absolute_datetime(dt):
        return format_datetime(
            dt.astimezone(user_tz),
            format="EEEE d MMMM @ HH:mm",
            locale=Locale("fr", "FR"),
        )

    def duration(reference, target):
        humanize.activate("fr_FR")
        delta = target - reference
        if abs(delta.total_seconds()) < 10 * 60:
            return "en même temps"
        elif delta > timedelta(0):
            return f"{humanize.naturaldelta(delta)} après"
        else:
            return f"{humanize.naturaldelta(-delta)} avant"

    return {
        "absolute_datetime": absolute_datetime,
        "duration": duration,
    }


def add_logos(_any):
    return {
        "logos_info": {
            m.name: {
                "background_color": m.logo_background_color,
                "content": m.logo_content,
                "src": m.logo_src,
            }
            for m in media_collection.values()
        }
    }


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(
    directory="templates", context_processors=[add_date_processing, add_logos]
)


storage = None


async def get_db():
    global storage

    if storage is None:
        storage = await Storage.create()

    return storage


async def get_similarity_search(storage: Storage = Depends(get_db)):
    return SimilaritySearch.load(storage)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, storage: Storage = Depends(get_db)):
    sites = await storage.list_sites()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"page_title": "Observatoire des médias", "sites": sites},
    )


@app.get("/sites/{id}/main_article", response_class=HTMLResponse)
@app.get("/sites/{id}/main_article/{timestamp}", response_class=HTMLResponse)
async def site_main_article_snapshot(
    request: Request,
    id: int,
    timestamp: datetime | None = None,
    storage: Storage = Depends(get_db),
    sim_index: SimilaritySearch = Depends(get_similarity_search),
):
    def get_article_sibling(after_before_articles, cond_fun):
        return min(
            [a for a in after_before_articles if cond_fun(a)],
            key=lambda a: abs(a["time_diff"]),
            default=None,
        )

    main_articles = await storage.list_neighbouring_main_articles(id, timestamp)

    [focused_article] = [
        a for a in main_articles if a["site_id"] == id and a["time_diff"] == 0
    ]
    simultaneous_articles = sorted(
        [a for a in main_articles if a["site_id"] != id and a["time_diff"] == 0],
        key=lambda a: a["site_id"],
    )
    same_site_articles = [
        a for a in main_articles if a["site_id"] == id and a["time_diff"] != 0
    ]

    focused_title_id = focused_article["title_id"]
    try:
        [(_, similar)] = await sim_index.search(
            [focused_title_id],
            20,
            lambda s: s < 100 and s >= 25,
        )
    except KeyError:
        similar = []

    similar_by_id = {s[0]: s[1] for s in similar}
    similar_articles = await storage.list_snapshot_apparitions(
        list(similar_by_id.keys())
    )
    # A list of articles and score, sorted by descending score
    similar_articles_and_score = sorted(
        [
            (a, similar_by_id[a["title_id"]])
            for a in similar_articles
            if a["title_id"] != focused_title_id
        ],
        key=lambda a: a[1],
        reverse=True,
    )

    return templates.TemplateResponse(
        request=request,
        name="site_main_article_detail.html",
        context={
            "site_id": id,
            "focused": focused_article,
            "similar": similar_articles_and_score,
            "simultaneous_up": [
                a
                for a in simultaneous_articles
                if a["site_id"] < focused_article["site_id"]
            ],
            "simultaneous_down": [
                a
                for a in simultaneous_articles
                if a["site_id"] > focused_article["site_id"]
            ],
            "after": get_article_sibling(
                same_site_articles,
                lambda a: a["time_diff"] > 0,
            ),
            "before": get_article_sibling(
                same_site_articles,
                lambda a: a["time_diff"] < 0,
            ),
        },
    )
