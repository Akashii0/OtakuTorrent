# flake8: noqa: E501

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Path, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
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
        content, url = get_anime_page_content(anime_url)
        metadata = extract_anime_metadata(content)
        return {
            "poster_link": metadata.poster_link,
            "summary": metadata.summary,
            "genres": metadata.genres,
            "release_year": metadata.release_year,
            "episode_count": metadata.episode_count,
            "airing_status": metadata.airing_status.name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {e}")
    