class UpstreamBadRequest(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UpstreamRateLimited(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UpstreamServiceUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
