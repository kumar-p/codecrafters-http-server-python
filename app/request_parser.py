from app.http_request import HTTPRequest


# Exception Hierarchy
class HTTPParseError(Exception):
    """Base exception for HTTP parsing errors"""

    pass


class EmptyRequestError(HTTPParseError):
    """Raised when request bytes are empty"""

    pass


class InvalidEncodingError(HTTPParseError):
    """Raised when request cannot be decoded as UTF-8"""

    pass


class InvalidRequestLineError(HTTPParseError):
    """Raised when request line format is invalid"""

    pass


class InvalidHTTPMethodError(HTTPParseError):
    """Raised when HTTP method is not supported"""

    pass


class InvalidHeaderError(HTTPParseError):
    """Raised when header format is malformed"""

    pass


# HTTP Protocol Constants
SUPPORTED_HTTP_METHODS = frozenset(
    {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}
)
REQUEST_LINE_SEPARATOR = "\r\n"
HEADER_BODY_SEPARATOR = "\r\n\r\n"
HEADER_KEY_VALUE_SEPARATOR = ":"
DEFAULT_ENCODING = "utf-8"


class RequestParser:
    """HTTP request parser with validation and error handling"""

    @staticmethod
    def parse(raw_bytes: bytes) -> HTTPRequest:
        """
        Parse raw HTTP request bytes into HTTPRequest object.

        Args:
            raw_bytes: Raw HTTP request as bytes

        Returns:
            HTTPRequest object with parsed data

        Raises:
            HTTPParseError: If request is malformed or invalid
        """
        # Validate input is not empty
        if not raw_bytes:
            raise EmptyRequestError("Received empty request")

        # Try to decode UTF-8
        try:
            request = raw_bytes.decode(DEFAULT_ENCODING)
        except UnicodeDecodeError as e:
            raise InvalidEncodingError(f"Invalid UTF-8 encoding: {e}")

        # Split into request line, headers, and body
        req_line, _, headers_and_content = request.partition(REQUEST_LINE_SEPARATOR)
        header_string, _, body = headers_and_content.partition(HEADER_BODY_SEPARATOR)

        # Parse request line
        method, path = RequestParser._parse_request_line(req_line)

        # Validate HTTP method
        RequestParser._validate_http_method(method)

        # Parse URL to get request name and query parameter
        route, route_param = RequestParser._parse_url(path)

        # Parse headers
        headers = RequestParser._parse_headers(header_string)

        # Construct and return HTTPRequest
        return HTTPRequest(
            method=method,
            path=path,
            headers=headers,
            body=body,
            route=route,
            route_param=route_param,
        )

    @staticmethod
    def _parse_request_line(line: str) -> tuple[str, str]:
        """
        Parse HTTP request line into method and path.

        Args:
            line: Request line string (e.g., "GET /path HTTP/1.1")

        Returns:
            Tuple of (method, path)

        Raises:
            InvalidRequestLineError: If request line format is invalid
        """
        components = line.split(" ")
        if len(components) < 2:
            raise InvalidRequestLineError(
                f"Invalid request line format. Expected at least 2 components, got {len(components)}"
            )

        method = components[0]
        path = components[1]
        return method, path

    @staticmethod
    def _parse_url(path: str) -> tuple[str, str]:
        """
        Parse URL path to extract endpoint name and parameter.

        Args:
            path: URL path (e.g., "/echo/hello")

        Returns:
            Tuple of (request_name, query_param)
        """
        request_name, _, param = path.strip("/").partition("/")
        return request_name.lower(), param

    @staticmethod
    def _parse_headers(header_string: str) -> dict[str, str]:
        """
        Parse header string into dictionary.

        Args:
            header_string: Raw headers string

        Returns:
            Dictionary of header key-value pairs
        """
        headers_dict: dict[str, str] = {}
        for header in header_string.split(REQUEST_LINE_SEPARATOR):
            if HEADER_KEY_VALUE_SEPARATOR in header:
                key, value = header.split(HEADER_KEY_VALUE_SEPARATOR, 1)
                headers_dict[key.strip().lower()] = value.strip()
        return headers_dict

    @staticmethod
    def _validate_http_method(method: str) -> None:
        """
        Validate HTTP method is supported.

        Args:
            method: HTTP method to validate

        Raises:
            InvalidHTTPMethodError: If method is not supported
        """
        if method not in SUPPORTED_HTTP_METHODS:
            raise InvalidHTTPMethodError(
                f"Unsupported HTTP method: {method}. "
                f"Supported methods: {', '.join(sorted(SUPPORTED_HTTP_METHODS))}"
            )
