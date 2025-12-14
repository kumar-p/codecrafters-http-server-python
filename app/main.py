import socket  # noqa: F401


NOT_FOUND = "HTTP/1.1 404 Not Found\r\n\r\n"
OK = "HTTP/1.1 200 OK"
HOST = "localhost"
PORT = 4221

def main():

    with socket.create_server((HOST, PORT)) as server:
        while True:
            connection, client_address = server.accept()
            print("Connected by", client_address)
            with connection:
                req = connection.recv(1024)
                url, req_headers = get_request_contents(req)
                request_name, url_param = get_url_contents(url)
                resp = NOT_FOUND
                if request_name == "":
                    resp = f"{OK}\r\n\r\n"
                elif request_name == "echo":
                    resp = get_echo_response(url_param)
                elif request_name == "user-agent":
                    resp = get_user_agent_response(req_headers)
                print(f"\nSending the response:\n{resp}")
                connection.sendall(resp.encode())


def get_echo_response(url_param):
    return get_response_with_text(url_param)


def get_user_agent_response(headers):
    user_agent = headers["User-Agent"]
    return get_response_with_text(user_agent.strip())


def get_response_with_text(body_text) -> str:
    content_length = len(body_text)
    headers = f"Content-type: text/plain\r\nContent-Length: {content_length}"
    resp = f"{OK}\r\n{headers}\r\n\r\n{body_text}"
    return resp


def get_url_contents(url):
    request_name, _, param =  url.strip("/").partition("/")
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
