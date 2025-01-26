# flake8: noqa: E501

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List
from app.scrapper.services import (
    search,
    extract_anime_metadata,
    extract_anime_id,
    get_anime_page_content,
    get_download_page_links,
    GetDirectDownloadLinks,
    dub_availability_and_link,
)
from app.scrapper.schemas.base import (
    SearchResult,
    AnimeMetadataResponse,
    DownloadLinkResponse,
    DubAvailabilityResponse,
)
from pydantic import HttpUrl


def validate_episode_range(start: int, end: int):
    if start > end or start < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid episode range: start must be <= end and >= 1",
        )


router = APIRouter()


@router.get("/welcome")
async def hello():
    """Welcome Endpoint"""
    return JSONResponse(
        content={
            "message": "Welcome to the OtakuTorrent, an Anime Scraper and Downloader API",
            "endpoints": {
                "/search": "Search for anime by keyword",
                "/metadata": "Fetch metadata for an anime",
                "/dub-availability": "Check if a dubbed version exists",
                "/download-links": "Get episode download links",
            }    
        }
    )


@router.get("/search", response_model=List[SearchResult])
async def search_anime(
    keyword: str = Query(..., description="Anime name to search"),
    ignore_dub: bool = Query(True, description="Ignore dub availability"),
):
    """Search anime by Keyword."""
    try:
        results = search(keyword, ignore_dub=ignore_dub)
        if not results:
            raise HTTPException(status_code=404, detail="No results found")
        return [{"title": title, "link": link} for title, link in results]
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/metadata", response_model=AnimeMetadataResponse)
async def get_metadata(
    anime_url: HttpUrl = Query(..., description="Anime URL"),
):
    """Get anime metadata from URL."""
    try:
        content, url = get_anime_page_content(str(anime_url))
        metadata = extract_anime_metadata(content)

        # # Ensure airing_status is an Enum
        # if not isinstance(metadata.airing_status, Enum):
        #     raise ValueError("Airing status must be an Enum")

        return {
            "poster_url": metadata.poster_url,
            "summary": metadata.summary,
            "genres": metadata.genres,
            "release_year": metadata.release_year,
            "episode_count": metadata.episode_count,
            "airing_status": (
                metadata.airing_status
                # if isinstance(metadata.airing_status, AiringStatus)
                # else str(metadata.airing_status)
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {e}")


@router.get("/dub-availability", response_model=DubAvailabilityResponse)
async def check_dub(
    anime_title: str = Query(..., description="Anime title for dubbed Version"),
):
    """Check if a dubbed version is available"""
    try:
        available, link = dub_availability_and_link(anime_title)
        return {"dub_available": available, "link": link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/download_links", response_model=DownloadLinkResponse)
async def download_links(
    background_tasks: BackgroundTasks,
    anime_url: HttpUrl = Query(..., description="Anime title"),
    start_episode: int = Query(..., description="Start episode", ge=1),
    end_episode: int = Query(..., description="End episode", ge=1),
    quality: str = Query("720", description="Preferred video Quality"),
):
    """Fetch download links for episodes of a specific anime"""
    try:
        validate_episode_range(start_episode, end_episode)

        content, url = get_anime_page_content(str(anime_url))
        anime_id = extract_anime_id(content)
        download_page_links = get_download_page_links(start_episode, end_episode, anime_id)

        downloader = GetDirectDownloadLinks()

        # Progress callback for tracking
        def progress_callback(completed: int):
            print(f"Progress: {completed} episodes processed.")\
        
        background_tasks.add_task(
            downloader.get_direct_download_links,
            download_page_links,
            quality,
            progress_update_callback=progress_callback
        )

        direct_download_links, sizes = downloader.get_direct_download_links(download_page_links, quality)
        if not direct_download_links:
            raise HTTPException(status_code=404, detail="No direct download links available")
        return {"download_links": direct_download_links, "sizes": sizes}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")