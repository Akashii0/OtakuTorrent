# Flake8: noqa: E501
from typing import List
from pydantic import BaseModel, Field, HttpUrl
from app.common.scraper import AiringStatus

class SearchResult(BaseModel):
    title: str = Field(..., examples=["Naruto", "Naruto Shippuden"])
    link: HttpUrl = Field(..., examples=["https://gogoanime.so/category/naruto", "https://gogoanime.so/category/naruto-shippuden"])


class AnimeMetadataResponse(BaseModel):
    poster_url: HttpUrl = Field(..., examples=["https://gogoanime.so/anime/naruto/cover", "https://gogoanime.so/anime/naruto-shippuden/cover"])
    summary: str = Field(..., examples=["Naruto is a young ninja who seeks recognition from his peers and dreams of becoming the Hokage, the leader of his village.", "Naruto Shippuden is a continuation of the original Naruto series."])
    genres: List[str] = Field(..., examples=[["Action", "Adventure", "Comedy", "Super Power", "Martial Arts", "Shounen"], ["Action", "Adventure", "Comedy", "Super Power", "Martial Arts", "Shounen"]])
    release_year: int = Field(..., examples=[2002, 2007])
    episode_count: int = Field(..., examples=[220, 500])
    airing_status: str = Field(..., examples=["FINISHED", "FINISHED"])
    # airing_status: AiringStatus


class DownloadLinkResponse(BaseModel):
    download_links: List[HttpUrl] = Field(..., examples="https://gogoanime.so/download/naruto-shippuden-episode-1")
    sizes: List[int] = Field(..., examples=[100, 200])


class DubAvailabilityResponse(BaseModel):
    dub_available: bool = Field(..., examples=[True, False])
    dub_link: HttpUrl = Field(..., examples=["https://gogoanime.so/category/naruto-dub", "https://gogoanime.so/category/naruto-shippuden-dub"])
