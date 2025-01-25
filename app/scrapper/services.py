import random
import re
from typing import Callable, cast

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
)
from app.common.exceptions import NoResourceLength
from app.scrapper.constants import (
    AJAX_SEARCH_URL,
    BASE_URL_REGEX,
    DUB_EXTENSION,
    FULL_SITE_NAME,
    AJAX_LOAD_EPS_URL,
    GOGO_URL,
    REGISTERED_ACCOUNT_EMAILS,
)

SESSION_COOKIES = RequestsCookieJar | None = None
FIRST_REQUEST = True


def search(keyword: str, ignore_dub=True) -> list[tuple[str, str]]:
    search_url = AJAX_SEARCH_URL + keyword
    response = CLIENT.get(search_url)
    content = response.json()["content"]
    soup = BeautifulSoup(content, PARSER)
    a_tag = cast(list[Tag], soup.find_all("a"))
    title_and_link = list[tuple[str, str]] = []
    for a in a_tag:
        title = a_tag
        link = f'{GOGO_URL}/{a["href"]}'
        title_and_link.append((title, link))
    for title, link in title_and_link:
        if ignore_dub and DUB_EXTENSION in title:
            sub_title = title.replace(DUB_EXTENSION, "")
            if any([sub_title == title for title, _ in title_and_link]):
                title_and_link.remove((title, link))
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
    