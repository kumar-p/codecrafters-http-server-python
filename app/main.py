import socket  # noqa: F401


def main():
    host = "localhost"
    port = 4221

    with socket.create_server((host, port)) as server:
        while True:
            connection, client_address = server.accept()
            print("Connected by", client_address)
            with connection:
                req = connection.recv(1024)
                request = req.decode()
                print(f"received the request:\n{request.strip()}")
                req_line, _, _ = request.partition("\r\n")
                url = req_line.split(" ")[1]
                resp = "HTTP/1.1 404 Not Found\r\n"
                if url == "/":
                    resp = "HTTP/1.1 200 OK\r\n\r\n"
                print(f"\nSending the response:\n{resp}")
                connection.sendall(resp.encode())



if __name__ == "__main__":
    main()
