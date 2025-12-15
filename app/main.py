import argparse
import logging
from app.HTTPServer import HTTPServer

HOST = "localhost"
PORT = 4221

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="./", help="Files directory")
    args = parser.parse_args()
    files_directory = args.directory
    http_server = HTTPServer(
        logger, host=HOST, port=PORT, files_directory=files_directory
    )
    http_server.start()


if __name__ == "__main__":
    main()
