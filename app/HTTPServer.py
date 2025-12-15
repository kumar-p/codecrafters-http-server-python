import os
import socket
from logging import Logger
from threading import Thread


class HTTPServer:
    NOT_FOUND = "HTTP/1.1 404 Not Found\r\n\r\n"
    OK = "HTTP/1.1 200 OK"
    CREATED = "HTTP/1.1 201 Created\r\n\r\n"
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
                    verb, url, req_headers, content = self.get_request_contents(req)
                    request_name, url_param = self.get_url_contents(url)
                    resp = self.create_response(
                        verb, request_name, url_param, req_headers, content
                    )
                    connection.sendall(resp.encode())
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
        self, verb, request_name, url_param, req_headers: dict[str, str], content
    ) -> str:
        resp = HTTPServer.NOT_FOUND
        if request_name == "":
            resp = f"{HTTPServer.OK}\r\n\r\n"
        elif request_name == "echo":
            resp = self.get_echo_response(url_param)
        elif request_name == "user-agent":
            resp = self.get_user_agent_response(req_headers)
        elif request_name == "files":
            resp = self.get_file_response(
                self.files_directory, verb, url_param, content
            )
        self.logger.debug(f"\nSending the response:\n{resp:50}")
        return resp

    def get_echo_response(self, url_param):
        return self.get_response_with_text(url_param)

    def get_user_agent_response(self, headers):
        user_agent = headers["User-Agent"]
        return self.get_response_with_text(user_agent.strip())

    def get_request_contents(self, req: bytes):
        request = req.decode()
        req_line, _, headers_and_content = request.partition("\r\n")
        req_components = req_line.split(" ")
        verb = req_components[0]
        url = req_components[1]
        header_string, _, content = headers_and_content.partition("\r\n\r\n")
        headers_dict = self.get_headers_dict(header_string)
        return verb, url, headers_dict, content

    def get_file_response(self, files_directory, verb, file_name, content):
        file_path = os.path.join(files_directory, file_name)
        if verb == "GET":
            if os.path.isfile(file_path):
                file_text = self.read_file(file_path)
                content_length = len(file_text)
                headers = f"Content-Type: application/octet-stream\r\nContent-Length: {content_length}"
                resp = f"{HTTPServer.OK}\r\n{headers}\r\n\r\n{file_text}"
                return resp
        elif verb == "POST":
            self.write_file(file_path, content)
            return HTTPServer.CREATED
        return HTTPServer.NOT_FOUND

    @staticmethod
    def get_response_with_text(body_text) -> str:
        content_length = len(body_text)
        headers = f"Content-Type: text/plain\r\nContent-Length: {content_length}"
        resp = f"{HTTPServer.OK}\r\n{headers}\r\n\r\n{body_text}"
        return resp

    @staticmethod
    def read_file(file_path):
        with open(file_path, "r") as file:
            file_text = file.read()
            return file_text

    @staticmethod
    def write_file(file_path, content):
        with open(file_path, "w") as file:
            file.write(content)

    @staticmethod
    def get_url_contents(url):
        request_name, _, param = url.strip("/").partition("/")
        return request_name.lower(), param

    @staticmethod
    def get_headers_dict(header_string):
        headers_dict = {}
        for header in header_string.split("\r\n"):
            key, value = header.split(":", 1)
            headers_dict[key] = value
        return headers_dict
