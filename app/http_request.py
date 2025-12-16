from dataclasses import dataclass


@dataclass
class HTTPRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: str
    route: str
    route_param: str
