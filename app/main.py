from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect

from app.routers.main import router as main_router
from app.routers.search import router as search_router
from app.db.database import Base, engine
from app.models import user, wishlist
from contextlib import asynccontextmanager

app = FastAPI(title="PriceWatch — MVP")

Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(main_router)
app.include_router(search_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    inspector = inspect(engine)
    print("Existing tables:", inspector.get_table_names())
    yield
    print("Shutting down...")
