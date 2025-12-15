import argparse
import os
import socket
import logging
from threading import Thread

NOT_FOUND = "HTTP/1.1 404 Not Found\r\n\r\n"
OK = "HTTP/1.1 200 OK"
HOST = "localhost"
PORT = 4221
CONNECTION_TIMEOUT = 5.0  # seconds
BUFFER_SIZE = 1024

parser = argparse.ArgumentParser()
parser.add_argument("--directory", default="./", help="Files directory")
args = parser.parse_args()
files_directory = args.directory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    with socket.create_server((HOST, PORT), reuse_port=True) as server:
        logger.info(f"Listening on {HOST}:{PORT}")
        while True:
            connection, client_address = server.accept()
            thread = Thread(
                target=on_client_connection,
                args=(connection, client_address),
                daemon=True,
            )
            thread.start()


def on_client_connection(connection, client_address):
    logger.info(f"Connection received from: {client_address}")
    with connection:
        connection.settimeout(CONNECTION_TIMEOUT)
        while True:
            try:
                logger.debug(f"Waiting for data from {client_address}...")
                req = connection.recv(BUFFER_SIZE)
                if not req:
                    logger.info(f"Connection closed by {client_address}")
                    break

                logger.info(f"Received {len(req)} bytes from {client_address}")
                url, req_headers = get_request_contents(req)
                request_name, url_param = get_url_contents(url)
                resp = create_response(request_name, url_param, req_headers)
                connection.sendall(resp.encode())
                logger.info(f"Sent response to {client_address}")

            except socket.timeout:
                logger.debug(f"Connection timeout for {client_address} (idle)")
                break
            except Exception as e:
                logger.error(
                    f"Error while processing request for {client_address}: {e}",
                    exc_info=True,
                )
                break


def create_response(request_name, url_param, req_headers: dict[str, str]) -> str:
    resp = NOT_FOUND
    if request_name == "":
        resp = f"{OK}\r\n\r\n"
    elif request_name == "echo":
        resp = get_echo_response(url_param)
    elif request_name == "user-agent":
        resp = get_user_agent_response(req_headers)
    elif request_name == "files":
        resp = get_file_response(url_param)
    logger.debug(f"\nSending the response:\n{resp:50}")
    return resp


def get_echo_response(url_param):
    return get_response_with_text(url_param)


def get_user_agent_response(headers):
    user_agent = headers["User-Agent"]
    return get_response_with_text(user_agent.strip())


def get_response_with_text(body_text) -> str:
    content_length = len(body_text)
    headers = f"Content-Type: text/plain\r\nContent-Length: {content_length}"
    resp = f"{OK}\r\n{headers}\r\n\r\n{body_text}"
    return resp


def get_file_response(file_name):
    file_path = os.path.join(files_directory, file_name)
    if os.path.isfile(file_path):
        with open(file_name, "r") as file:
            file_text = file.read()
            content_length = len(file_text)
            headers = f"Content-Type: application/octet-stream\r\nContent-Length: {content_length}"
            resp = f"{OK}\r\n{headers}\r\n\r\n{file_text}"
            return resp
    return NOT_FOUND


def get_url_contents(url):
    request_name, _, param = url.strip("/").partition("/")
    return request_name.lower(), param


def get_request_contents(req: bytes):
    request = req.decode()
    req_line, _, headers_and_content = request.partition("\r\n")
    url = req_line.split(" ")[1]
    header_string = headers_and_content.partition("\r\n\r\n")[0]
    headers_dict = get_headers_dict(header_string)
    return url, headers_dict


def get_headers_dict(header_string):
    headers_dict = {}
    for header in header_string.split("\r\n"):
        key, value = header.split(":", 1)
        headers_dict[key] = value
    return headers_dict


if __name__ == "__main__":
    main()
