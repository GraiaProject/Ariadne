# 适配器

`Ariadne` 的适配器用于建立与 `mirai-api-http` 的连接.

!!! info "请参阅 [API 文档](graia.ariadne.adapter)"

## 正向适配器

正向适配器作为客户端连接至 `mirai-api-http`, 有以下几种类型.

- [`WebsocketAdapter`][graia.ariadne.adapter.forward.WebsocketAdapter] 正向 Websocket

- [`HttpAdapter`][graia.ariadne.adapter.forward.HttpAdapter] 正向 HTTP

- [`ComposeForwardAdapter`][graia.ariadne.adapter.forward.ComposeForwardAdapter] 正向 Websocket + HTTP

正向适配器均有一个 `ForwardAdapter.session` 对应着其 [`aiohttp.ClientSession`][aiohttp.ClientSession] 对象.

## 反向适配器

反向适配器作为服务端让 `mirai-api-http` 进行连接, 有以下几种类型.

!!! warning "所有带有 `Compose` 前缀的反向适配器中 `MiraiSession` 仍需要填写 `host` 字段"

!!! info "你可以直接安装 `uvicorn[standard]`, `fastapi` 包, 或通过 `graia-ariadne[server]` / `graia-ariadne[full]` 获取"

- [`ComposeWebhookAdapter`][graia.ariadne.adapter.reverse.ComposeWebhookAdapter] 正向 HTTP + 反向 HTTP

- [`ComposeReverseWebsocketAdapter`][graia.ariadne.adapter.reverse.ComposeReverseWebsocketAdapter] 正向 HTTP + 反向 Websocket

- [`ReverseWebsocketAdapter`][graia.ariadne.adapter.reverse.ReverseWebsocketAdapter] 纯反向 Websocket

这些反向适配器需要传入 `route` 与 `port` 作为服务路径 (默认 `#!py "/"` ) 与服务器端口 (默认 `#!py 8000` )，多余的关键字参数会传入 `uvicorn.Config`.

同时，因为使用了 [`FastAPI`](https://fastapi.tiangolo.com/zh), 你可以直接通过 `ReverseAdapter.asgi` 属性获取一个 `FastAPI` 实例.

`ReverseAdapter.server` 对应着其 `Uvicorn` 服务器.