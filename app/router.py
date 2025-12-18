"""Route dispatcher using handler registry pattern."""

from typing import Dict
from http import HTTPStatus
from app.http_request import HTTPRequest
from app.http_response import HttpResponse
from app.route_handler import RouteHandler


class Router:
    """
    Route dispatcher using handler registry.

    Maps route names to handler instances and dispatches
    requests to the appropriate handler.
    """

    def __init__(self):
        """Initialize router with empty handler registry."""
        self._handlers: Dict[str, RouteHandler] = {}

    def register(self, route: str, handler: RouteHandler) -> None:
        """
        Register a handler for a route.

        Args:
            route: Route name (e.g., "", "echo", "files")
            handler: Handler instance implementing RouteHandler protocol
        """
        self._handlers[route] = handler

    def dispatch(self, request: HTTPRequest) -> HttpResponse:
        """
        Dispatch request to appropriate handler.

        Args:
            request: Parsed HTTP request with route information

        Returns:
            HTTP response from handler, or 404 if no handler registered
        """
        handler = self._handlers.get(request.route)

        if handler is None:
            return HttpResponse(HTTPStatus.NOT_FOUND, {}, "")

        return handler.handle(request)

    def has_route(self, route: str) -> bool:
        """
        Check if route has a registered handler.

        Args:
            route: Route name to check

        Returns:
            True if handler registered for this route, False otherwise
        """
        return route in self._handlers
