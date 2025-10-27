# app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy.engine import Engine

from app.db.database import Base, engine as prod_engine
from app.routers.main import router as main_router
from app.routers.search import router as search_router
from app.routers.auth import router as auth_router

templates = Jinja2Templates(directory="app/templates")

def create_app(engine_override: Engine | None = None) -> FastAPI:
    engine_to_use = engine_override or prod_engine

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine_to_use)
        print("Existing tables:", inspect(engine_to_use).get_table_names())
        yield

    app = FastAPI(title="PriceWatch — MVP", lifespan=lifespan)

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(main_router)
    app.include_router(search_router)
    app.include_router(auth_router)


    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        accept = request.headers.get("accept", "")
        if exc.status_code == 401 and "text/html" in accept.lower():
            reasons = {
                "missing_token": "Вы не авторизованы. Пожалуйста, войдите.",
                "invalid_token": "Сессия некорректна. Выполните вход ещё раз.",
                "token_expired": "Сессия истекла. Пожалуйста, войдите снова.",
                "user_not_found": "Пользователь не найден. Зарегистрируйтесь или войдите.",
            }
            msg = reasons.get(str(exc.detail), "Требуется авторизация.")
            return templates.TemplateResponse("401.html", {"request": request, "message": msg}, status_code=401)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers or {})


    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
