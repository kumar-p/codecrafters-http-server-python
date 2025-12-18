"""Server-specific exceptions for better error handling."""


class HTTPServerError(Exception):
    """Base exception for HTTP server errors."""

    pass


class ConnectionError(HTTPServerError):
    """Errors related to socket connections."""

    pass


class RequestProcessingError(HTTPServerError):
    """Errors during request processing."""

    pass
