# flake8: noqa: E501

from contextlib import asynccontextmanager
from anyio import to_thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

description = """
## Welcome to the OtakuTorrent, an Anime Scraper and Downloader API 🚀🚀🚀

* **"/search"**: "Search for anime by keyword",
* **"/metadata"**: "Fetch metadata for an anime",
* **"/dub-availability"**: "Check if a dubbed version exists",
* **"/download-links"**: "Get episode download links",
"""

app = FastAPI(
    title="OtakuTorrent API",
    lifespan=lifespan,
    description=description,
    version="1.0.0",
    docs_url="/",
    contact={
        "name": "Akashi",
        "url": "https://akashi.7o7.cx",
        "email": "abdulkid151@gmail.com"
    }
)

# Allow all origins (for development only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scrapper_router, prefix="/api", tags=["Scrapper"])
