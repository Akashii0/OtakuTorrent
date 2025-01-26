# flake8: noqa: E501

import random
import re
from typing import Callable, List, Tuple, cast

from bs4 import BeautifulSoup, ResultSet, Tag
from requests.cookies import RequestsCookieJar
from app.common.scraper import (
    CLIENT,
    PARSER,
    AiringStatus,
    AnimeMetadata,
    DomainNameError,
    Download,
    ProgressFunction,
    closest_quality_index,
    sanitise_title,
)
from app.common.exceptions import NoResourceLength
from app.scrapper.constants import (
    AJAX_SEARCH_URL,
    BASE_URL_REGEX,
    DUB_EXTENSION,
    AJAX_LOAD_EPS_URL,
    GOGO_URL,
    REGISTERED_ACCOUNT_EMAILS,
)

SESSION_COOKIES: RequestsCookieJar | None = None
FIRST_REQUEST = True


# def search(keyword: str, ignore_dub=True) -> list[tuple[str, str]]:
#     search_url = AJAX_SEARCH_URL + keyword
#     response = CLIENT.get(search_url)
#     content = response.json()["content"]
#     soup = BeautifulSoup(content, PARSER)
#     a_tag = cast(list[Tag], soup.find_all("a"))

#     # title_and_link = list[tuple[str, str]] = []
#     title_and_link: list[tuple[str, str]] = []

#     for a in a_tag:
#         title = a_tag
#         link = f'{GOGO_URL}/{a["href"]}'
#         title_and_link.append((title, link))
#     for title, link in title_and_link:
#         if ignore_dub and DUB_EXTENSION in title:
#             sub_title = title.replace(DUB_EXTENSION, "")
#             if any([sub_title == title for title, _ in title_and_link]):
#                 title_and_link.remove((title, link))
#     return title_and_link

def search(keyword: str, ignore_dub=True) -> List[Tuple[str, str]]:
    search_url = AJAX_SEARCH_URL + keyword
    response = CLIENT.get(search_url)
    content = response.json()["content"]
    
    # Parse HTML content
    soup = BeautifulSoup(content, PARSER)
    
    # Find all relevant <a> tags with the "ss-title" class
    a_tags = soup.find_all("a", class_="ss-title")
    
    # Initialize the list to store (title, URL) pairs
    title_and_link: List[Tuple[str, str]] = []
    
    # Extract title and URL from each <a> tag
    for a_tag in a_tags:
        title = a_tag.get_text(strip=True)
        href = f'{GOGO_URL}/{a_tag["href"]}'  # Append the base URL to the href
        title_and_link.append((title, href))
    
    # Optionally filter out dubbed entries
    if ignore_dub:
        filtered_results = []
        for title, link in title_and_link:
            if DUB_EXTENSION in title:
                # Check if the subbed version of the title exists
                sub_title = title.replace(DUB_EXTENSION, "")
                if any(sub_title == t for t, _ in title_and_link):
                    continue  # Skip the dubbed version if subbed exists
            filtered_results.append((title, link))
        title_and_link = filtered_results
    
    return title_and_link


def extract_anime_id(anime_page_content: bytes) -> int:
    soup = BeautifulSoup(anime_page_content, PARSER)
    anime_id = cast(str, cast(Tag, soup.find("input", id="movie_id"))["value"])
    return int(anime_id)


def title_is_sub(title: str) -> bool:
    return DUB_EXTENSION in title


def get_download_page_links(
        start_episode: int, end_episode: int, anime_id: int
) -> list[str]:
    ajax_url = AJAX_LOAD_EPS_URL.format(start_episode, end_episode, anime_id)
    content = CLIENT.get(ajax_url).content
    soup = BeautifulSoup(content, PARSER)
    a_tags = soup.find_all("a")
    download_page_links: list[str] = []
    # Reversed cause their ajax api returns the episodes in reverse order i.e 3, 2, 1
    for a in reversed(a_tags):
        resource = cast(str, a["href"]).strip()
        download_page_links.append(GOGO_URL + resource)
    return download_page_links


class GetDirectDownloadLinks(ProgressFunction):
    def __init__(self) -> None:
        super().__init__()

    def get_direct_download_links(
            self,
            download_page_links: list[str],
            user_quality: str,
            progress_update_callback: Callable[[int], None] | None = None,   
    ) -> tuple[list[str], list[int]]:
        direct_download_links: list[str] = []
        download_sizes: list[int] = []
        for eps_pg_link in download_page_links:
            link = ""
            size = 0
            while True:
                response = CLIENT.get(eps_pg_link, cookies=get_session_cookies())
                soup = BeautifulSoup(response.content, PARSER)
                a_tags = cast(
                    ResultSet[Tag],
                    cast(Tag, soup.find("div", class_="cf-download")).find_all("a"),
                )
                qualities = [a.text for a in a_tags]
                idx = closest_quality_index(qualities, user_quality)
                link = cast(str, a_tags[idx]["href"])
                if not link:
                    continue
                try:
                    size, link = Download.get_resource_length(link)
                    break
                except NoResourceLength:
                    continue
            direct_download_links.append(link)
            download_sizes.append(size)
            self.resume.wait()
            if self.cancelled:
                return [], []
            if progress_update_callback:
                progress_update_callback(1)
        return direct_download_links, download_sizes
    

def get_anime_page_content(anime_page_link: str) -> tuple[bytes, str]:
    global FIRST_REQUEST
    global GOGO_URL
    try:
        response = CLIENT.get(
            anime_page_link,
            allow_redirects=True,
            exceptions_to_raise=(DomainNameError, KeyboardInterrupt),
        )
        if not response.history:
            return response.content, anime_page_link
        new_anime_page_link = response.url.replace("http://", "https://")
        if new_anime_page_link == anime_page_link:
            raise DomainNameError(Exception("Redirected but provided the same domain"))
        match = cast(re.Match[str], BASE_URL_REGEX.search(new_anime_page_link))
        GOGO_URL = match.group(1)
        return get_anime_page_content(new_anime_page_link)
    except DomainNameError:
        if not FIRST_REQUEST:
            raise
        FIRST_REQUEST = False
        prev_home_url = GOGO_URL
        return get_anime_page_content(
            anime_page_link.replace(prev_home_url, GOGO_URL)
        )
    

def extract_anime_metadata(anime_page_content: bytes) -> AnimeMetadata:
    soup = BeautifulSoup(anime_page_content, PARSER)
    poster_link = cast(
        str,
        cast(Tag, cast(Tag, soup.find(class_="anime_info_body_bg")).find("img"))["src"],
    )
    summary = cast(Tag, soup.find(class_="description")).get_text()
    metadata_tags = soup.find_all("p", class_="type")
    genre_tags = cast(ResultSet[Tag], metadata_tags[2].find_all("a"))
    genres = cast(list[str], [g["title"] for g in genre_tags])
    release_year = int(metadata_tags[3].get_text().replace("Released: ", ""))
    episode_count = int(
        cast(
            Tag,
            cast(
                ResultSet[Tag],
                cast(Tag, soup.find("ul", id="episode_page")).find_all("li"),
            )[-1].find("a"),
        )
        .get_text()
        .split("-")[-1]
    )
    tag = soup.find("a", title="Ongoing Anime")
    if episode_count == 0:
        airing_status = AiringStatus.UPCOMING
    elif tag:
        airing_status = AiringStatus.ONGOING
    else:
        airing_status = AiringStatus.FINISHED
    return AnimeMetadata(
        poster_link, summary, genres, release_year, episode_count, airing_status
    )


def dub_availability_and_link(anime_title: str) -> tuple[bool, str]:
    dub_title = f"{anime_title}{DUB_EXTENSION}"
    results = search(dub_title, False)
    sanitised_dub_title = sanitise_title(dub_title, True)
    for res_title, link in results:
        if sanitised_dub_title == sanitise_title(res_title, True):
            return True, link
    return False, ""


def get_session_cookies(fresh=False) -> RequestsCookieJar:
    global SESSION_COOKIES
    if SESSION_COOKIES and not fresh:
        return SESSION_COOKIES
    login_url = f"{GOGO_URL}/login.html"
    response = CLIENT.get(login_url)
    soup = BeautifulSoup(response.content, PARSER)
    form_div = cast(Tag, soup.find("div", class_="form-login"))
    csrf_token = cast(Tag, form_div.find("input", {"name": "_csrf"}))["value"]
    form_data = {
        "email": random.choice(REGISTERED_ACCOUNT_EMAILS),
        "password": "amogus69420",
        "_csrf": csrf_token,
    }
    # A valid User-Agent is required during this post request hence the CLIENT is technically only necessary here
    response = CLIENT.post(login_url, form_data, cookies=response.cookies)
    SESSION_COOKIES = response.cookies
    if not SESSION_COOKIES:
        return get_session_cookies()
    return SESSION_COOKIES
