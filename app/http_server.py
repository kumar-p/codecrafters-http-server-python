"""Multithreaded HTTP/1.1 server with routing support."""

import logging
import socket
from http import HTTPStatus
from logging import Logger
from threading import Thread

from app.http_constants import HTTPHeaders
from app.file_manager import FileManager
from app.http_request import HTTPRequest
from app.http_response import HttpResponse
from app.request_parser import HTTPParseError, RequestParser
from app.route_handler import EchoHandler, FileHandler, RootHandler, UserAgentHandler
from app.router import Router


class HTTPServer:
    """
    Multithreaded HTTP/1.1 server.

    Features:
    - Thread-per-connection model
    - Configurable timeouts
    - Compression support (gzip)
    - Persistent connections (Connection: keep-alive/close)
    - Pluggable routing via Router
    """

    CONNECTION_TIMEOUT = 5.0  # seconds
    BUFFER_SIZE = 1024

    def __init__(
        self,
        logger: Logger,
        host: str,
        port: int,
        files_directory: str,
        router: Router | None = None,
    ):
        """
        Initialize HTTP server.

        Args:
            logger: Logger instance for debug/info/error messages
            host: Host address to bind to
            port: Port number to listen on
            files_directory: Directory for file operations
            router: Optional Router instance (creates default if None)
        """
        self.logger = logger
        self.host = host
        self.port = port
        self.files_directory = files_directory

        # Initialize router with default handlers
        self.router = router or self._create_default_router()

    def _create_default_router(self) -> Router:
        """
        Create router with standard handlers.

        Returns:
            Router instance with registered handlers
        """
        router = Router()

        # Register standard routes
        router.register("", RootHandler())
        router.register("echo", EchoHandler())
        router.register("user-agent", UserAgentHandler())

        # File handler needs FileManager
        try:
            file_manager = FileManager(self.files_directory, self.logger)
            router.register("files", FileHandler(file_manager))
        except (ValueError, FileNotFoundError) as e:
            self.logger.warning(
                f"File handler not available: {e}. /files route will return 404"
            )

        return router

    def start(self):
        """Start server and accept connections."""
        with socket.create_server((self.host, self.port), reuse_port=True) as server:
            self.logger.info(f"Listening on {self.host}:{self.port}")
            while True:
                connection, client_address = server.accept()
                thread = Thread(
                    target=self._handle_connection,
                    args=(connection, client_address),
                    daemon=True,
                )
                thread.start()

    def _handle_connection(self, connection: socket.socket, client_address):
        """
        Handle single client connection (runs in thread).

        Args:
            connection: Client socket connection
            client_address: Client address tuple (host, port)
        """
        self.logger.info(f"Connection from: {client_address}")

        with connection:
            connection.settimeout(HTTPServer.CONNECTION_TIMEOUT)

            while True:
                try:
                    # Receive request
                    raw_request = self._receive_request(connection, client_address)
                    if raw_request is None:
                        # Connection closed gracefully
                        break

                    # Parse request
                    try:
                        http_request = RequestParser.parse(raw_request)
                    except HTTPParseError as e:
                        self.logger.warning(
                            f"Invalid request from {client_address}: {e}"
                        )
                        self._send_error_response(connection, HTTPStatus.BAD_REQUEST)
                        continue

                    # Process request through router
                    response = self.router.dispatch(http_request)

                    # Handle Connection header
                    should_close = self._should_close_connection(http_request, response)

                    # Send response
                    compression = http_request.headers.get(HTTPHeaders.ACCEPT_ENCODING)
                    connection.sendall(response.to_bytes(compression=compression))
                    self.logger.info(f"Sent response to {client_address}")

                    if should_close:
                        break

                except socket.timeout:
                    self.logger.debug(f"Connection timeout for {client_address}")
                    break
                except OSError as e:
                    # Socket errors (connection reset, broken pipe, etc.)
                    self.logger.warning(f"Socket error for {client_address}: {e}")
                    break
                except Exception as e:
                    # Unexpected errors - log and close connection
                    self.logger.error(
                        f"Unexpected error for {client_address}: {e}",
                        exc_info=True,
                    )
                    try:
                        self._send_error_response(
                            connection, HTTPStatus.INTERNAL_SERVER_ERROR
                        )
                    except Exception as e:
                        logging.exception(f"Unexpected error for {client_address}: {e}")
                    break

    def _receive_request(
        self, connection: socket.socket, client_address
    ) -> bytes | None:
        """
        Receive request bytes from connection.

        Args:
            connection: Client socket connection
            client_address: Client address for logging

        Returns:
            Request bytes or None if connection closed by client
        """
        self.logger.debug(f"Waiting for data from {client_address}")
        data = connection.recv(HTTPServer.BUFFER_SIZE)

        if not data:
            self.logger.info(f"Connection closed by {client_address}")
            return None

        self.logger.info(f"Received {len(data)} bytes from {client_address}")
        return data

    @staticmethod
    def _should_close_connection(request: HTTPRequest, response: HttpResponse) -> bool:
        """
        Determine if connection should be closed.

        HTTP/1.1 defaults to keep-alive unless Connection: close.

        Args:
            request: HTTP request to check for Connection header
            response: HTTP response to update with Connection header

        Returns:
            True if connection should close, False to keep alive
        """
        connection_header = request.headers.get(HTTPHeaders.CONNECTION, "").lower()

        if connection_header == "close":
            response.headers["Connection"] = "close"
            return True

        return False

    @staticmethod
    def _send_error_response(connection: socket.socket, status: HTTPStatus) -> None:
        """
        Send simple error response.

        Args:
            connection: Client socket connection
            status: HTTP status code to send
        """
        response = HttpResponse(status, {}, status.phrase)
        try:
            connection.sendall(response.to_bytes())
        except OSError:
            pass  # Best effort
