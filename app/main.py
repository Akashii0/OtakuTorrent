# flake8: noqa: E501

from contextlib import asynccontextmanager
from anyio import to_thread
from fastapi import FastAPI
from app.scrapper.api import router as scrapper_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """This is the Startup and Shutdown"""
    print("Awaken your anime journey!")
    
    # Bigger Threadpool i.e you send a bunch of reqs it will handle them concurrently
    limiter = to_thread.current_default_thread_limiter()
    limiter.total_tokens = 1000

    # Shutdown Code
    yield
    print("Adventure complete. Until next time!")


app = FastAPI(
    title="OtakuTorrent API",
    lifespan=lifespan,
    description="API for OtakuTorrent",
    version="1.0.0",
    docs_url="/",
    contact={
        "name": "Akashi",
        "url": "https://akashi.7o7.cx",
        "email": "abdulkid151@gmail.com"
    }
)

app.include_router(scrapper_router, prefix="/api", tags=["Scrapper"])
