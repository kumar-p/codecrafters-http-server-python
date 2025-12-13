import socket  # noqa: F401


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    host = "localhost"
    port = 4221

    with socket.create_server((host, port)) as server:
        while True:
            connection, client_address = server.accept()
            with connection:
                _ = connection.recv(1024)
                resp = "HTTP/1.1 200 OK\r\n\r\n"
                print(f"{client_address[0]}:{client_address[1]}: {resp}")
                connection.sendall(resp.encode())



if __name__ == "__main__":
    main()
