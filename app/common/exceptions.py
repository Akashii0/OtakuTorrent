class NoResourceLength(Exception):
    def __init__(self, url: str, redirect_url: str) -> None:
        msg = (
            f'Received no resource length from "{url}"'
            if url == redirect_url
            else f'Received no resource length from "{url}" (redirected from "{redirect_url}")' # noqa
        )
        super().__init__(msg)


class DomainNameError(Exception):
    message = "Invalid domain name"

    def __init__(self, original_exception: Exception) -> None:
        super().__init__(DomainNameError.message, original_exception)
        self.original_exception = original_exception

