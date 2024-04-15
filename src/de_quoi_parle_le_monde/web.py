from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from de_quoi_parle_le_monde.medias import media_collection
from de_quoi_parle_le_monde.storage import Storage


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def get_db():
    return await Storage.create()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, storage: Storage = Depends(get_db)):
    sites = await storage.list_sites()
    return templates.TemplateResponse(request=request, name="index.html", context={"sites": sites})


@app.get("/sites/{id}/main_article", response_class=HTMLResponse)
async def site_main_article(request: Request, id: int, limit: int | None = None, storage: Storage = Depends(get_db)):
    opt_args = [limit] if limit is not None else []
    main_articles = await storage.list_main_articles(id, *opt_args)
    return templates.TemplateResponse(request=request, name="site_detail.html", context={"site_id": id, "main_articles": main_articles})


@app.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    return templates.TemplateResponse(request=request, name="admin/index.html", context={
        "collections": media_collection
    })
