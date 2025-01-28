# flake8: noqa: E501

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from requests.cookies import RequestsCookieJar
from typing import List
from bs4 import BeautifulSoup
import random
from app.common.scraper import CLIENT, PARSER
from app.scrapper.constants import GOGO_URL, REGISTERED_ACCOUNT_EMAILS
from app.scrapper.services import (
    search,
    extract_anime_metadata,
    extract_anime_id,
    get_anime_page_content,
    get_download_page_links,
    GetDirectDownloadLinks,
    dub_availability_and_link,
    get_session_cookies,
)
from app.scrapper.schemas.base import (
    SearchResult,
    AnimeMetadataResponse,
    DownloadLinkResponse,
    DubAvailabilityResponse,
)
from pydantic import HttpUrl
from tqdm import tqdm


def validate_episode_range(start: int, end: int):
    if start > end or start < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid episode range: start must be <= end and >= 1",
        )


router = APIRouter()


def fetch_session_cookies(fresh=False) -> RequestsCookieJar:
        try:
            global SESSION_COOKIES

            # Step 1: Retrieve the login page
            login_url = "https://anitaku.bz/login.html"
            response = CLIENT.get(login_url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to retrieve login page")

            # Step 2: Parse the login page
            soup = BeautifulSoup(response.content, PARSER)
            form_div = soup.find("div", class_="form-login")
            if not form_div:
                raise HTTPException(
                    status_code=500, detail="Login form not found on the login page"
                )

            csrf_input = form_div.find("input", {"name": "_csrf"})
            if not csrf_input or not csrf_input.has_attr("value"):
                raise HTTPException(
                    status_code=500, detail="CSRF token input not found or invalid"
                )

            csrf_token = csrf_input["value"]

            # Step 3: Submit the login form
            form_data = {
                "email": random.choice(REGISTERED_ACCOUNT_EMAILS),
                "password": "amogus69420",
                "_csrf": csrf_token,
            }
            response = CLIENT.post(login_url, data=form_data, cookies=response.cookies)
            
            # if response.status_code != 200 or not response.cookies:
            #     raise HTTPException(status_code=401, detail="Login failed")

            # Step 4: Store and return the session cookies
            SESSION_COOKIES = response.cookies
            return SESSION_COOKIES
        except Exception as e:
            print(e)


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


@router.websocket("/progress")
async def web_socket_endpoint(
    websocket: WebSocket,
    anime_url: HttpUrl,
    start_episode: int,
    end_episode: int,
    quality: str = "720",
):
    """Websocket endpoint for anime progress updates"""

    await websocket.accept()

    try:
        # Validate episode range
        validate_episode_range(start_episode, end_episode)

        # Fetch anime page content and extract anime ID
        content, _ = get_anime_page_content(str(anime_url))
        anime_id = extract_anime_id(content)

        # Get download page links for the specified episodes
        download_page_links = get_download_page_links(start_episode, end_episode, anime_id)

        # Initialize the Downloader
        downloader = GetDirectDownloadLinks()
        total_episodes = len(download_page_links)
        completed_episodes = 0

        await websocket.send_text(f"Starting download for {total_episodes} episodes.")

        # Process each episode link
        for episode_link in download_page_links:
            try:
                # Extract the download link and size for the episode

                direct_download_links, sizes = downloader.get_direct_download_links([episode_link], quality)

                completed_episodes += 1
                await websocket.send_json({
                    "status": "success",
                    "episode_link": episode_link,
                    "download_links": direct_download_links,
                    "size": sizes,
                    "progress": f"{completed_episodes}/{total_episodes}"
                })
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "episode_link": episode_link,
                    "error": str(e),
                    "progress": f"{completed_episodes}/{total_episodes}"
                })
        
        # Notify completion
        await websocket.send_text("All episodes processed successfully")
    except WebSocketDisconnect:
        print("Websocket client disconnected.")
    except Exception as e:
        await websocket.send_text(f"An error occurred: {e}")
        await websocket.close()


@router.get("/download_links")
async def download_links(
    # background_tasks: BackgroundTasks,
    anime_url: HttpUrl = Query(..., description="Anime title"),
    start_episode: int = Query(..., description="Start episode", ge=1),
    end_episode: int = Query(..., description="End episode", ge=1),
    quality: str = Query("720", description="Preferred video Quality"),
):
    """Fetch download links for episodes of a specific anime"""
    try:
        print(f"Validating episodes: {start_episode} to {end_episode}")
        validate_episode_range(start_episode, end_episode)

        # Fetch anime page content and extract anime ID
        print(f"Fetching anime page content for URL: {anime_url}")
        content, url = get_anime_page_content(str(anime_url))
        anime_id = extract_anime_id(content)

        # Get download page links for the specified episodes
        print(f"Fetching download page links for episodes {start_episode}-{end_episode}")
        download_page_links = get_download_page_links(start_episode, end_episode, anime_id)
        print(download_page_links)

        # Ensure valid session cookies
        print("Fetching session cookies")
        cookies = fetch_session_cookies()
        print(f"Session Cookies: {cookies}")

        # Initialize the downloader
        print("Initializing the downloader")
        downloader = GetDirectDownloadLinks()

        # Fetch direct download links
        print(f"Fetching direct download links for episodes {start_episode}-{end_episode}")
        direct_download_links, sizes = downloader.get_direct_download_links(download_page_links, quality, cookies=cookies)

        # if not direct_download_links:
        #     raise HTTPException(status_code=404, detail="No direct download links available")

        print("Download links fetched successfully")
        return {"download_links": direct_download_links, "sizes": sizes}
        # direct_download_links = ["http://example.com/download1", "http://example.com/download2"]
        # sizes = [500, 700]
        # return {"download_links": direct_download_links, "sizes": sizes}

    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/progress-ui", response_class=HTMLResponse)
async def websocket_ui():
    """Serve WebSocket UI for progress monitoring."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Progress Monitor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
            }
            #log {
                max-height: 300px;
                overflow-y: auto;
                border: 1px solid #ccc;
                padding: 10px;
                background: #f9f9f9;
            }
            .success {
                color: green;
            }
            .error {
                color: red;
            }
        </style>
    </head>
    <body>
        <h1>Anime Download Progress Monitor</h1>
        <div>
            <label for="anime_url">Anime URL:</label>
            <input type="text" id="anime_url" value="https://example.com/anime" />
            <br />
            <label for="start_episode">Start Episode:</label>
            <input type="number" id="start_episode" value="1" />
            <br />
            <label for="end_episode">End Episode:</label>
            <input type="number" id="end_episode" value="12" />
            <br />
            <label for="quality">Quality:</label>
            <input type="text" id="quality" value="720" />
            <br />
            <button onclick="startWebSocket()">Start WebSocket</button>
        </div>
        <h2>Log</h2>
        <div id="log"></div>

        <script>
            let ws;

            function startWebSocket() {
                const animeUrl = document.getElementById("anime_url").value;
                const startEpisode = document.getElementById("start_episode").value;
                const endEpisode = document.getElementById("end_episode").value;
                const quality = document.getElementById("quality").value;

                const logDiv = document.getElementById("log");
                logDiv.innerHTML = ""; // Clear previous logs

                const wsUrl = `ws://localhost:8000/progress?anime_url=${encodeURIComponent(animeUrl)}&start_episode=${startEpisode}&end_episode=${endEpisode}&quality=${quality}`;
                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    const log = document.createElement("div");
                    log.textContent = "WebSocket connection established.";
                    logDiv.appendChild(log);
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    const log = document.createElement("div");

                    if (data.status === "success") {
                        log.textContent = `Processed: ${data.progress} - Download Link: ${data.download_links}`;
                        log.classList.add("success");
                    } else if (data.status === "error") {
                        log.textContent = `Error processing episode: ${data.episode_link}, Error: ${data.error}`;
                        log.classList.add("error");
                    } else {
                        log.textContent = data; // General progress or completion messages
                    }

                    logDiv.appendChild(log);
                    logDiv.scrollTop = logDiv.scrollHeight; // Auto-scroll to the bottom
                };

                ws.onclose = () => {
                    const log = document.createElement("div");
                    log.textContent = "WebSocket connection closed.";
                    logDiv.appendChild(log);
                };
            }
        </script>
    </body>
    </html>
    """


@router.post("/login")
def login():
    """
    Login and refresh the session cookies.
    """

    # SESSION_COOKIES: RequestsCookieJar | None = None
    def fetch_session_cookies(fresh=False) -> RequestsCookieJar:
        try:
            global SESSION_COOKIES

            # Step 1: Retrieve the login page
            login_url = "https://anitaku.bz/login.html"
            response = CLIENT.get(login_url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to retrieve login page")

            # Step 2: Parse the login page
            soup = BeautifulSoup(response.content, PARSER)
            form_div = soup.find("div", class_="form-login")
            if not form_div:
                raise HTTPException(
                    status_code=500, detail="Login form not found on the login page"
                )

            csrf_input = form_div.find("input", {"name": "_csrf"})
            if not csrf_input or not csrf_input.has_attr("value"):
                raise HTTPException(
                    status_code=500, detail="CSRF token input not found or invalid"
                )

            csrf_token = csrf_input["value"]

            # Step 3: Submit the login form
            form_data = {
                "email": random.choice(REGISTERED_ACCOUNT_EMAILS),
                "password": "amogus69420",
                "_csrf": csrf_token,
            }
            response = CLIENT.post(login_url, data=form_data, cookies=response.cookies)
            
            # if response.status_code != 200 or not response.cookies:
            #     raise HTTPException(status_code=401, detail="Login failed")

            # Step 4: Store and return the session cookies
            SESSION_COOKIES = response.cookies
            return SESSION_COOKIES
        except Exception as e:
            print(e)
    cookies = fetch_session_cookies()
    return {"message": "Login successful", "cookies": str(cookies)}
