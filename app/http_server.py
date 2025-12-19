"""Async HTTP/1.1 server with routing support."""

import asyncio
import logging
from http import HTTPStatus
from logging import Logger

from app.http_constants import HTTPHeaders
from app.file_manager import FileManager
from app.http_request import HTTPRequest
from app.http_response import HttpResponse
from app.request_parser import HTTPParseError, RequestParser
from app.route_handler import EchoHandler, FileHandler, RootHandler, UserAgentHandler
from app.router import Router


class HTTPServer:
    """
    Async HTTP/1.1 server using asyncio.

    Features:
    - Asyncio-based concurrent connection handling
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

    async def start(self):
        """Start async server and accept connections."""
        server = await asyncio.start_server(
            self._handle_connection, self.host, self.port
        )
        self.logger.info(f"Listening on {self.host}:{self.port}")

        async with server:
            await server.serve_forever()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Handle single client connection asynchronously.

        Args:
            reader: Async stream reader for receiving data
            writer: Async stream writer for sending data
        """
        client_address = writer.get_extra_info("peername")
        self.logger.info(f"Connection from: {client_address}")

        try:
            while True:
                # Receive request with timeout
                raw_request = await self._receive_request(reader, client_address)
                if raw_request is None:
                    break

                # Parse request (synchronous - no change needed)
                try:
                    http_request = RequestParser.parse(raw_request)
                except HTTPParseError as e:
                    self.logger.warning(f"Invalid request from {client_address}: {e}")
                    error_response = HttpResponse(
                        HTTPStatus.BAD_REQUEST, {}, HTTPStatus.BAD_REQUEST.phrase
                    )
                    await self._send_response(writer, error_response.to_bytes())
                    continue

                # Dispatch to router (synchronous - no change needed)
                response = self.router.dispatch(http_request)

                # Check connection close
                should_close = self._should_close_connection(http_request, response)

                # Send response
                compression = http_request.headers.get(HTTPHeaders.ACCEPT_ENCODING)
                await self._send_response(
                    writer, response.to_bytes(compression=compression)
                )
                self.logger.info(f"Sent response to {client_address}")

                if should_close:
                    break

        except asyncio.TimeoutError:
            self.logger.debug(f"Connection timeout for {client_address}")
        except asyncio.IncompleteReadError:
            self.logger.debug(f"Client disconnected: {client_address}")
        except OSError as e:
            self.logger.warning(f"Socket error for {client_address}: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error for {client_address}: {e}", exc_info=True
            )
            try:
                error_response = HttpResponse(HTTPStatus.INTERNAL_SERVER_ERROR, {}, "")
                await self._send_response(writer, error_response.to_bytes())
            except Exception as e:
                logging.exception(f"Failed to send error response: {e}")
        finally:
            # Close writer without waiting - prevents async exceptions during load testing
            if not writer.is_closing():
                writer.close()

    async def _receive_request(
        self, reader: asyncio.StreamReader, client_address
    ) -> bytes | None:
        """
        Receive request bytes from async stream with timeout.

        Args:
            reader: Async stream reader
            client_address: Client address for logging

        Returns:
            Request bytes or None if connection closed/timeout
        """
        self.logger.debug(f"Waiting for data from {client_address}")

        try:
            data = await asyncio.wait_for(
                reader.read(HTTPServer.BUFFER_SIZE),
                timeout=HTTPServer.CONNECTION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self.logger.debug(f"Read timeout for {client_address}")
            return None

        if not data:
            self.logger.info(f"Connection closed by {client_address}")
            return None

        self.logger.info(f"Received {len(data)} bytes from {client_address}")
        return data

    @staticmethod
    async def _send_response(
        writer: asyncio.StreamWriter, response_bytes: bytes
    ) -> None:
        """
        Send response bytes to async stream.

        Args:
            writer: Async stream writer
            response_bytes: Response data to send
        """
        writer.write(response_bytes)
        await writer.drain()

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
