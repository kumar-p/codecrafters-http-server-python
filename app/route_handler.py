"""Route handlers using protocol pattern for extensibility."""

from typing import Protocol
from http import HTTPStatus
from app.http_request import HTTPRequest
from app.http_response import HttpResponse
from app.file_manager import FileManager, FileSecurityError
import app.http_constants as constants


class RouteHandler(Protocol):
    """Protocol for route handlers (structural subtyping)."""

    def handle(self, request: HTTPRequest) -> HttpResponse:
        """
        Handle HTTP request and return response.

        Args:
            request: Parsed HTTP request

        Returns:
            HTTP response to send to client
        """
        ...


class RootHandler:
    """Handler for root path '/'."""

    def handle(self, request: HTTPRequest) -> HttpResponse:
        """Return 200 OK with empty body."""
        return HttpResponse(HTTPStatus.OK, {}, "")


class EchoHandler:
    """Handler for /echo/<text> - echoes back the text."""

    def handle(self, request: HTTPRequest) -> HttpResponse:
        """Echo the route parameter as text/plain."""
        headers = {"Content-Type": "text/plain"}
        return HttpResponse(HTTPStatus.OK, headers, request.route_param)


class UserAgentHandler:
    """Handler for /user-agent - returns User-Agent header."""

    def handle(self, request: HTTPRequest) -> HttpResponse:
        """Return the User-Agent header value."""
        user_agent = request.headers.get(constants.HTTPHeaders.USER_AGENT, "")
        headers = {"Content-Type": "text/plain"}
        return HttpResponse(HTTPStatus.OK, headers, user_agent.strip())


class FileHandler:
    """Handler for /files/<filename> - GET/POST file operations."""

    def __init__(self, file_manager: FileManager):
        """
        Initialize FileHandler with a FileManager.

        Args:
            file_manager: FileManager instance for secure file operations
        """
        self.file_manager = file_manager

    def handle(self, request: HTTPRequest) -> HttpResponse:
        """
        Route file operations based on HTTP method.

        Args:
            request: HTTP request with file path in route_param

        Returns:
            HTTP response (200/201/404/403/405/500)
        """
        match request.method:
            case "GET":
                return self._handle_get(request)
            case "POST":
                return self._handle_post(request)
            case _:
                return HttpResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"Allow": "GET, POST"}, ""
                )

    def _handle_get(self, request: HTTPRequest) -> HttpResponse:
        """
        Handle GET request to read file.

        Args:
            request: HTTP request with filename in route_param

        Returns:
            200 with file content, 404 if not found, 403 if forbidden, 500 on error
        """
        try:
            content = self.file_manager.read_file(request.route_param)
            headers = {"Content-Type": "application/octet-stream"}
            return HttpResponse(HTTPStatus.OK, headers, content)
        except FileNotFoundError:
            return HttpResponse(HTTPStatus.NOT_FOUND, {}, "")
        except FileSecurityError:
            # Log security violation but return generic 403
            return HttpResponse(HTTPStatus.FORBIDDEN, {}, "")
        except PermissionError:
            return HttpResponse(HTTPStatus.FORBIDDEN, {}, "")
        except Exception:
            # Unexpected errors become 500
            return HttpResponse(HTTPStatus.INTERNAL_SERVER_ERROR, {}, "")

    def _handle_post(self, request: HTTPRequest) -> HttpResponse:
        """
        Handle POST request to write file.

        Args:
            request: HTTP request with filename in route_param and content in body

        Returns:
            201 on success, 403 if forbidden, 500 on error
        """
        try:
            # Encode string body to bytes for binary write
            content = (
                request.body.encode("utf-8")
                if isinstance(request.body, str)
                else request.body
            )
            self.file_manager.write_file(request.route_param, content)
            return HttpResponse(HTTPStatus.CREATED, {}, "")
        except FileSecurityError:
            return HttpResponse(HTTPStatus.FORBIDDEN, {}, "")
        except PermissionError:
            return HttpResponse(HTTPStatus.FORBIDDEN, {}, "")
        except Exception:
            return HttpResponse(HTTPStatus.INTERNAL_SERVER_ERROR, {}, "")
