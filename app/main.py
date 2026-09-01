import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api import admin, auth_routes, credentials, dashboard, inventory, wan_links
from app.config import settings
from app.monitoring.worker import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker.start()
    yield
    await worker.stop()


app = FastAPI(title="Frampol NOC", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_routes.router)
app.include_router(inventory.router)
app.include_router(wan_links.router)
app.include_router(credentials.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


def _require_session(request: Request) -> bool:
    return settings.skip_auth or bool(request.session.get("user_id"))


@app.get("/login")
def login_page(request: Request):
    if _require_session(request):
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/")
def dashboard_page(request: Request):
    if not _require_session(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/branches/{branch_id}")
def branch_overview_page(request: Request, branch_id: int):
    if not _require_session(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("branch_overview.html", {"request": request, "branch_id": branch_id})


@app.get("/wan-links/{wan_link_id}")
def wan_link_details_page(request: Request, wan_link_id: int):
    if not _require_session(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("wan_link_details.html", {"request": request, "wan_link_id": wan_link_id})


@app.get("/onboard")
def onboarding_page(request: Request):
    if not _require_session(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("onboarding.html", {"request": request})


@app.get("/settings")
def settings_page(request: Request):
    if not _require_session(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("settings.html", {"request": request})
