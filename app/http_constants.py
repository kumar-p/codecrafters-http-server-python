from enum import Enum


class HTTPHeaders(str, Enum):
    """Standard HTTP header names (lowercase per HTTP/1.1 spec)."""

    USER_AGENT = "user-agent"
    ACCEPT_ENCODING = "accept-encoding"
    CONNECTION = "connection"


class HTTPMethod(str, Enum):
    """Standard HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"


class StandardRoute(str, Enum):
    """Standard route names used in the server."""

    ROOT = ""
    ECHO = "echo"
    USER_AGENT = "user-agent"
    FILES = "files"
