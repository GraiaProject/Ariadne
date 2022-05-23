from typing import Dict, List, NamedTuple, Type, Union

from ._info import (
    HttpClientInfo,
    HttpServerInfo,
    U_Info,
    WebsocketClientInfo,
    WebsocketServerInfo,
)


class WebsocketClientConfig(NamedTuple):
    """Websocket 客户端配置"""

    host: str = "http://localhost:8080"
    """mirai-api-http 的 Endpoint"""


class WebsocketServerConfig(NamedTuple):
    """Websocket 服务器配置"""

    path: str = "/"
    """服务的 Endpoint"""
    params: Dict[str, str] = {}
    """用于验证的参数"""
    headers: Dict[str, str] = {}
    """用于验证的请求头"""


class HttpClientConfig(NamedTuple):
    """HTTP 客户端配置"""

    host: str = "http://localhost:8080"
    """mirai-api-http 的 Endpoint"""


class HttpServerConfig(NamedTuple):
    """HTTP 服务器配置"""

    path: str = "/"
    """服务的 Endpoint """

    headers: Dict[str, str] = {}
    """用于验证的请求头"""


U_Config = Union[HttpClientConfig, WebsocketClientConfig, WebsocketServerConfig, HttpServerConfig]

_CFG_INFO_MAP = {
    HttpClientConfig: HttpClientInfo,
    WebsocketClientConfig: WebsocketClientInfo,
    WebsocketServerConfig: WebsocketServerInfo,
    HttpServerConfig: HttpServerInfo,
}


def config(account: int, verify_key: str, *configs: Union[Type[U_Config], U_Config]) -> List[U_Info]:
    """生成 Ariadne 账号配置

    Args:
        account (int): 账号
        verify_key (str): mirai-api-http 使用的 VerifyKey
        *configs (Union[Type[U_Config], U_Config]): 配置, 为 \
            `HttpClientConfig`, `WebsocketClientConfig`, \
            `WebsocketServerConfig`, `HttpServerConfig` 类或实例

    Returns:
        List[U_Info]: 配置列表, 可直接传给 `Ariadne` 类
    """
    assert isinstance(account, int)
    assert isinstance(verify_key, str)
    configs = configs or (HttpClientConfig(), WebsocketClientConfig())
    infos: List[U_Info] = []
    for cfg in configs:
        if isinstance(cfg, type):
            cfg = cfg()
        infos.append(_CFG_INFO_MAP[type(cfg)](account, verify_key, *cfg))
    return infos
