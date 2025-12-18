from pathlib import Path
import socket
from http import HTTPStatus
from logging import Logger
from threading import Thread
from app.http_request import HTTPRequest
from app.http_response import HttpResponse
from app.request_parser import RequestParser, HTTPParseError

USER_AGENT = "user-agent"
ACCEPT_ENCODING = "accept-encoding"


class HTTPServer:
    CONNECTION_TIMEOUT = 5.0  # seconds
    BUFFER_SIZE = 1024

    def __init__(self, logger: Logger, host: str, port: int, files_directory: str):
        self.logger = logger
        self.host = host
        self.port = port
        self.files_directory = files_directory

    def start(self):
        with socket.create_server((self.host, self.port), reuse_port=True) as server:
            self.logger.info(f"Listening on {self.host}:{self.port}")
            while True:
                connection, client_address = server.accept()
                thread = Thread(
                    target=self.on_client_connection,
                    args=(connection, client_address),
                    daemon=True,
                )
                thread.start()

    def on_client_connection(self, connection, client_address):
        self.logger.info(f"Connection received from: {client_address}")
        with connection:
            connection.settimeout(HTTPServer.CONNECTION_TIMEOUT)
            while True:
                try:
                    self.logger.debug(f"Waiting for data from {client_address}...")
                    req = connection.recv(HTTPServer.BUFFER_SIZE)
                    if not req:
                        self.logger.info(f"Connection closed by {client_address}")
                        break

                    self.logger.info(f"Received {len(req)} bytes from {client_address}")
                    try:
                        http_request = RequestParser.parse(req)
                    except HTTPParseError as e:
                        self.logger.warning(
                            f"Invalid request from {client_address}: {e}"
                        )
                        resp = HttpResponse(HTTPStatus.BAD_REQUEST, {}, "Bad Request")
                        connection.sendall(resp.to_bytes())
                        continue
                    resp = self.create_response(http_request)
                    compression = http_request.headers.get(ACCEPT_ENCODING)
                    connection.sendall(resp.to_bytes(compression=compression))
                    self.logger.info(f"Sent response to {client_address}")

                except socket.timeout:
                    self.logger.debug(f"Connection timeout for {client_address} (idle)")
                    break
                except Exception as e:
                    self.logger.error(
                        f"Error while processing request for {client_address}: {e}",
                        exc_info=True,
                    )
                    break

    def create_response(
        self,
        http_request: HTTPRequest,
    ) -> HttpResponse:
        match http_request.route:
            case "":
                return HttpResponse(HTTPStatus.OK, {}, "")
            case "echo":
                return self.get_response_with_text(http_request.route_param)
            case "user-agent":
                return self.get_user_agent_response(http_request.headers)
            case "files":
                return self.get_file_response(self.files_directory, http_request)
            case _:
                return HttpResponse(HTTPStatus.NOT_FOUND, {}, "")

    def get_user_agent_response(self, headers: dict[str, str]) -> HttpResponse:
        user_agent = headers.get(USER_AGENT, "")
        return self.get_response_with_text(user_agent.strip())

    def get_file_response(
        self, files_directory: str, http_request: HTTPRequest
    ) -> HttpResponse:
        file_path = Path(files_directory) / http_request.route_param
        match http_request.method:
            case "GET":
                if not file_path.is_file():
                    return HttpResponse(HTTPStatus.NOT_FOUND, {}, "")
                file_text = self.read_file(file_path)
                headers = {
                    "Content-Type": "application/octet-stream",
                }
                return HttpResponse(HTTPStatus.OK, headers, file_text)
            case "POST":
                self.write_file(file_path, http_request.body)
                return HttpResponse(HTTPStatus.CREATED, {}, "")
            case _:
                return HttpResponse(HTTPStatus.NOT_FOUND, {}, "")

    @staticmethod
    def get_response_with_text(body_text: str) -> HttpResponse:
        headers = {"Content-Type": "text/plain"}
        return HttpResponse(HTTPStatus.OK, headers, body_text)

    @staticmethod
    def read_file(file_path: Path) -> str:
        return file_path.read_text()

    @staticmethod
    def write_file(file_path: Path, content: str) -> None:
        file_path.write_text(content)
