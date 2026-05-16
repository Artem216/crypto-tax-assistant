"""Domain and upstream exception types."""


class InvalidTransactionPayload(ValueError):
    """Raised when transaction input cannot be normalized."""


class UpstreamBadResponse(Exception):
    """Raised when CoinGecko returns an unexpected response payload."""


class UpstreamRateLimited(Exception):
    """Raised when CoinGecko rate-limits the request."""


class UpstreamServiceUnavailable(Exception):
    """Raised when CoinGecko is unavailable or times out."""
