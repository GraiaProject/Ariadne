from typing import Dict, NamedTuple, TypeVar, Union

from yarl import URL


class HttpClientInfo(NamedTuple):
    account: int
    verify_key: str
    host: str

    def get_url(self, route: str) -> str:
        return str((URL(self.host) / route))


class WebsocketClientInfo(NamedTuple):
    account: int
    verify_key: str
    host: str

    def get_url(self, route: str) -> str:
        return str((URL(self.host) / route))


class WebsocketServerInfo(NamedTuple):
    account: int
    verify_key: str
    path: str
    params: Dict[str, str]
    headers: Dict[str, str]


class HttpServerInfo(NamedTuple):
    account: int
    path: str
    headers: Dict[str, str]


U_Info = Union[HttpClientInfo, WebsocketClientInfo, WebsocketServerInfo, HttpServerInfo]

T_Info = TypeVar("T_Info", bound=U_Info)
