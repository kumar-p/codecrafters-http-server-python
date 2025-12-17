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
        body_content = self.body

        use_compression = self._negotiate_compression(compression)

        if use_compression:
            body_content = self._compress_content(self.body, use_compression)
            headers_lines.append(f"Content-Encoding: {use_compression}")

        headers_lines.append(f"Content-Length: {str(len(body_content))}")
        response_parts = [status_line, *headers_lines, "", body_content]
        return "\r\n".join(response_parts).encode()

    @staticmethod
    def _compress_content(body: str, compression: str) -> str:
        return body

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
