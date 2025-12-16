from http import HTTPStatus
from dataclasses import dataclass


SUPPORTED_COMPRESSIONS = frozenset({"gzip"})


@dataclass
class HttpResponse:
    status: HTTPStatus
    headers: dict[str, str]
    body: str

    def to_bytes(self, compression=None) -> bytes:
        status_line = f"HTTP/1.1 {self.status.value} {self.status.phrase}"
        headers_lines = [f"{key}: {value}" for key, value in self.headers.items()]
        body_content = self.body

        if compression in SUPPORTED_COMPRESSIONS:
            body_content = self.compress_content(self.body, compression)
            headers_lines.append(f"Content-Encoding: {compression}")

        headers_lines.append(f"Content-Length: {str(len(body_content))}")
        response_parts = [status_line, *headers_lines, "", body_content]
        return "\r\n".join(response_parts).encode()

    @staticmethod
    def compress_content(body: str, compression: str) -> str:
        return body
