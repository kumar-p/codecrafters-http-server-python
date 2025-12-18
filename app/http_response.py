import gzip
from http import HTTPStatus
from dataclasses import dataclass

SUPPORTED_COMPRESSIONS = frozenset({"gzip"})


@dataclass
class HttpResponse:
    status: HTTPStatus
    headers: dict[str, str]
    body: str

    def to_bytes(self, compression: str | None = None) -> bytes:
        status_line = f"HTTP/1.1 {self.status.value} {self.status.phrase}"
        headers_lines = [f"{key}: {value}" for key, value in self.headers.items()]

        use_compression = self._negotiate_compression(compression)
        body_content = self._encode_content(self.body, use_compression, headers_lines)

        headers_lines.append(f"Content-Length: {len(body_content)}")
        response_parts_without_body = [status_line, *headers_lines, "\r\n"]
        response_without_body = "\r\n".join(response_parts_without_body).encode()
        response = response_without_body + body_content
        return response

    @staticmethod
    def _encode_content(body: str, compression: str | None, headers_lines: list[str]) -> bytes:
        match compression:
            case "gzip":
                headers_lines.append(f"Content-Encoding: {compression}")
                return gzip.compress(body.encode())
            case _:
                return body.encode()

    @staticmethod
    def _negotiate_compression(accept_encoding: str | None) -> str | None:
        """
        Negotiate compression based on Accept-Encoding header.

        Parses the Accept-Encoding header, which can contain multiple
        compression schemes separated by commas (e.g., "gzip, deflate, br").
        Returns the first supported compression scheme, or None if no
        supported schemes are requested.

        Args:
            accept_encoding: Client's Accept-Encoding header value

        Returns:
            Selected compression scheme or None
        """
        if not accept_encoding:
            return None

        requested = [c.strip() for c in accept_encoding.split(",")]
        supported = [c for c in requested if c in SUPPORTED_COMPRESSIONS]
        return next(iter(supported), None)
