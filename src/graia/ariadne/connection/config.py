from typing import Dict, List, NamedTuple, Type, Union

from ._info import (
    HttpClientInfo,
    HttpServerInfo,
    U_Info,
    WebsocketClientInfo,
    WebsocketServerInfo,
)


class HttpClientConfig(NamedTuple):
    host: str = "http://localhost:8080"


class WebsocketClientConfig(NamedTuple):
    host: str = "http://localhost:8080"


class WebsocketServerConfig(NamedTuple):
    path: str = "/"
    params: Dict[str, str] = {}
    headers: Dict[str, str] = {}


class HttpServerConfig(NamedTuple):
    path: str = "/"
    headers: Dict[str, str] = {}


U_Config = Union[HttpClientConfig, WebsocketClientConfig, WebsocketServerConfig, HttpServerConfig]

_CFG_INFO_MAP = {
    HttpClientConfig: HttpClientInfo,
    WebsocketClientConfig: WebsocketClientInfo,
    WebsocketServerConfig: WebsocketServerInfo,
    HttpServerConfig: HttpServerInfo,
}


def config(account: int, verify_key: str, *configs: Union[Type[U_Config], U_Config]) -> List[U_Info]:
    configs = configs or (HttpClientConfig(), WebsocketClientConfig())
    infos: List[U_Info] = []
    for cfg in configs:
        if isinstance(cfg, type):
            cfg = cfg()
        infos.append(_CFG_INFO_MAP[type(cfg)](account, verify_key, *cfg))
    return infos
