import re

GOGO = "gogo"
GOGO_URL = "https://anitaku.so"
AJAX_ENTRY_POINT = "https://ajax.gogocdn.net"
AJAX_SEARCH_URL = f"{AJAX_ENTRY_POINT}/site/loadAjaxSearch?keyword="
AJAX_LOAD_EPS_URL = (
    f"{AJAX_ENTRY_POINT}/ajax/load-list-episode?ep_start={{}}&ep_end={{}}&id={{}}"  # noqa: E501
)
FULL_SITE_NAME = "Gogoanime"
DUB_EXTENSION = " (Dub)"

KEYS_REGEX = re.compile(rb"(?:container|videocontent)-(\d+)")
ENCRYPTED_DATA_REGEX = re.compile(rb'data-value="(.+?)"')
BASE_URL_REGEX = re.compile(r"(http[s]?://[a-zA-Z0-9\.\-]+)")
