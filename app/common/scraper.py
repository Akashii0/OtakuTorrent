# flake8: noqa: E501

from base64 import b64decode
from enum import Enum
import os
import random
import re
from threading import Event
import time
from typing import Callable, Iterator, TypeVar, cast
import requests

from app.common.exceptions import DomainNameError, NoResourceLength

T = TypeVar("T")
PARSER = "html.parser"
IBYTES_TO_MBS_DIVISOR = 1024 * 1024
QUALITY_REGEX_1 = re.compile(r"\b(\d{3,4})p\b")
QUALITY_REGEX_2 = re.compile(r"\b\d+x(\d+)\b")
NETWORK_RETRY_COUNT = 5

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 OPR/102.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 OPR/101.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.31",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.43",
    "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.41",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
)  # List of user agents for mobile devices

def has_valid_internet_connection() -> bool:
    """
    Check if the internet connection is valid.
    """
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False


class Client:
    def __init__(self) -> None:
        self.headers = self.setup_request_headers()

    def setup_request_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            # "Accept-Language": "en-US,en;q=0.5",
            # "Accept-Encoding": "gzip, deflate, br",
            # "Connection": "keep-alive",
            # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        return headers

    def append_headers(self, to_append: dict) -> dict:
        self.headers.update(to_append)
        return to_append

    def make_request(
        self,
        method: str,
        url: str,
        headers: dict | None,
        cookies={},
        stream=False,
        data: dict | bytes | None = None,
        json: dict | None = None,
        allow_redirects=False,
        timeout: int | None = None,
        exceptions_to_raise: tuple[type[BaseException], ...] = (KeyboardInterrupt),
    ) -> requests.Response:
        if not headers:
            headers = self.headers
        if method == "GET":

            def callback():
                return requests.get(
                    url,
                    headers=headers,
                    stream=stream,
                    cookies=cookies,
                    allow_redirects=allow_redirects,
                    timeout=timeout,
                )
        else:

            def callback():
                return requests.post(
                    url,
                    headers=headers,
                    cookies=cookies,
                    data=data,
                    json=json,
                    allow_redirects=allow_redirects,
                )

        return self.network_error_retry_wrapper(callback, exceptions_to_raise)

    def get(
        self,
        url: str,
        headers: dict | None = None,
        cookies={},
        stream=False,
        allow_redirects=False,
        timeout: int | None = None,
        exceptions_to_raise: tuple[type[BaseException], ...] = (KeyboardInterrupt),
    ) -> requests.Response:
        return self.make_request(
            "GET",
            url,
            headers,
            cookies=cookies,
            stream=stream,
            allow_redirects=allow_redirects,
            timeout=timeout,
            exceptions_to_raise=exceptions_to_raise,
        )

    def post(
        self,
        url: str,
        headers: dict | None = None,
        cookies={},
        data: dict | bytes | None = None,
        json: dict | None = None,
        allow_redirects=False,
        exceptions_to_raise: tuple[type[BaseException], ...] = (KeyboardInterrupt),
    ) -> requests.Response:
        return self.make_request(
            "POST",
            url,
            headers,
            data=data,
            json=json,
            cookies=cookies,
            allow_redirects=allow_redirects,
            exceptions_to_raise=exceptions_to_raise,
        )

    def network_error_retry_wrapper(
        self,
        callback: Callable[[], T],
        exceptions_to_raise: tuple[type[BaseException], ...] = (KeyboardInterrupt),
    ) -> T:
        while True:
            try:
                return callback()
            except requests.exceptions.RequestException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                if (
                    exceptions_to_raise is not None
                    and DomainNameError in exceptions_to_raise
                ):
                    e = DomainNameError(e) if has_valid_internet_connection() else e
                if exceptions_to_raise is not None and any(
                    [isinstance(e, exception) for exception in exceptions_to_raise]
                ):
                    raise e
                # log_exception(e)
                time.sleep(1)


CLIENT = Client()


class AiringStatus(Enum):
    ONGOING = "Ongoing"
    UPCOMING = "Upcoming"
    FINISHED = "Finished"

    def __eq__(self, other: object) -> bool:
        if type(self).__qualname__ != type(other).__qualname__:
            return False
        other = cast(AiringStatus, other)
        return self.value == other.value


class AnimeMetadata:
    def __init__(
            self,
            poster_url: str,
            summary: str,
            episode_count: int,
            airing_status: AiringStatus,
            genres: list[str],
            release_year: int,
    ):
        self.poster_url = poster_url
        self.summary = summary
        self.episode_count = episode_count
        self.airing_status = airing_status
        self.genres = genres
        self.release_year = release_year

    def get_poster_bytes(self) -> bytes:
        response = CLIENT.get(self.poster_url)
        return response.content


class ProgressFunction:
    def __init__(self) -> None:
        self.resume = Event()
        self.resume.set()
        self.cancelled = False

    def pause_or_resume(self) -> None:
        if self.resume.is_set():
            return self.resume.clear()
        self.resume.set()

    def cancel(self) -> None:
        if self.resume.is_set():
            self.cancelled = True


def try_deleting(path: str) -> None:
    if not os.path.isfile(path):
        return
    try:
        os.unlink(path)
    except PermissionError:
        pass


class Download(ProgressFunction):
    def __init__(
            self,
            link_or_segment_urls: str | list[str],
            episode_title: str,
            download_path: str,
            progress_update_callback: Callable = lambda _: None,
            file_extension=".mp4",
            is_hls_download=False,
            cookies=requests.sessions.RequestsCookieJar(),
    ) -> None:
        super().__init__()
        self.link_or_segment_urls = link_or_segment_urls
        self.episode_title = episode_title
        self.download_path = download_path
        self.progress_update_callback = progress_update_callback
        self.is_hls_download = is_hls_download
        self.cookies = cookies
        file_title = f"{self.episode_title}{file_extension}"
        self.file_path = os.path.join(self.download_path, file_title)
        ext = ".ts" if is_hls_download else file_extension
        temporary_file_title = f"{self.episode_title} [Downloading]{ext}"
        self.temporary_file_path = os.path.join(
            self.download_path, temporary_file_title
        )
        try_deleting(self.temporary_file_path)

    @staticmethod
    def get_resource_length(url: str) -> tuple[int, str]:
        response = CLIENT.get(url, stream=True, allow_redirects=True)
        resource_length_str = response.headers.get("Content-Length", None)
        redirect_url = response.url
        if resource_length_str is None:
            raise NoResourceLength(url, redirect_url)
        return (int(resource_length_str), redirect_url)
    
    def cancel(self):
        return super().cancel()
    
    def start_download(self):
        download_complete = False
        while not download_complete and not self.cancelled:
            download_complete = self.normal_download()
        if self.cancelled:
            try_deleting(self.temporary_file_path)
            return
        try_deleting(self.file_path)
        try:
            os.rename(self.temporary_file_path, self.file_path)
        except PermissionError:
            pass

    def normal_download(self) -> bool:
        self.link_or_segment_urls = cast(str, self.link_or_segment_urls)
        response = CLIENT.get(
            self.link_or_segment_urls,
            stream=True,
            timeout=30,
            cookies=self.cookies,
        )
    
        def response_ranged(start_byte_num: int) -> requests.Response:
            self.link_or_segment_urls = cast(str, self.link_or_segment_urls)
            return CLIENT.get(
                self.link_or_segment_urls,
                stream=True,
                headers=CLIENT.append_headers({"Range": f"bytes={start_byte_num}-"}),
                timeout=30,
                cookies=self.cookies,
            )
        
        total = int(response.headers.get("Content-Length", 0))

        def download(start_byte_num=0) -> bool:
            with open(
                self.temporary_file_path, "wb" if start_byte_num else "ab"
            ) as file:
                iter_content = cast(
                    Iterator[bytes],
                    response.iter_content(chunk_size=IBYTES_TO_MBS_DIVISOR)
                    if start_byte_num
                    else CLIENT.network_error_retry_wrapper(
                        lambda: response_ranged(start_byte_num).iter_content(
                            chunk_size=IBYTES_TO_MBS_DIVISOR
                        )
                    ),
                )
                while True:
                    try:
                        data = CLIENT.network_error_retry_wrapper(
                            lambda: next(iter_content)
                        )
                        self.resume.wait()
                        if self.cancelled:
                            return False
                        size = file.write(data)
                        self.progress_update_callback(size)
                    except StopIteration:
                        break
            
            file_size = os.path.getsize(self.temporary_file_path)
            return True if file_size >= total else download(file_size)
        
        return download()
  
if __name__ == "__main__":
    pass