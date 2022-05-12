from typing import Dict, TypeVar, Union

from pydantic import BaseModel, Field
from yarl import URL


class HttpClientConfig(BaseModel):
    account: int
    verify_key: str
    host: str = "http://localhost:8080"

    def get_url(self, route: str, **params) -> str:
        return str((URL(self.host) / route).with_query(params))


class WebsocketClientConfig(BaseModel):
    account: int
    verify_key: str
    host: str = "http://localhost:8080"

    def get_url(self, route: str, **params) -> str:
        return str((URL(self.host) / route).with_query(params))


class WebsocketServerConfig(BaseModel):
    account: int
    verify_key: str
    path: str = "/"
    params: Dict[str, str] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)


class HttpServerConfig(BaseModel):
    account: int
    path: str = "/"
    headers: Dict[str, str] = Field(default_factory=dict)


T_Config = TypeVar(
    "T_Config", HttpClientConfig, WebsocketClientConfig, WebsocketServerConfig, HttpServerConfig
)

ConfigUnion = Union[HttpClientConfig, WebsocketClientConfig, WebsocketServerConfig, HttpServerConfig]
