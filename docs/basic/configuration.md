# 配置相关

## 配置顺序

`Ariadne` 作为一个类可以通过 `config` 类方法进行全局定制, 包括默认账号, `Broadcast`, 事件循环, 安装富文本日志等.

参见 [`Ariadne.config`][graia.ariadne.app.Ariadne.config] 了解更多.

在创建任何 `Ariadne` 实例之后, 便不能再调用 `Ariadne.config` 了.

所以请在实例化之前配置好日志和默认账号等.

## 配置日志

从 `graia.ariadne.model` 导入 `LogConfig`.

`LogConfig` 是字典的子类, 里面的键都是 [`MiraiEvent`][graia.ariadne.event.MiraiEvent] 的子类,
值为对应的 **字符串**.

如果想要动态的改变日志级别, 可以传入一个签名为 `(MiraiEvent) -> str` 的方法.

如果想要彻底关闭日志, 直接调用 `app.log_config.clear()` 即可.

## 默认账号

如果你的 `Ariadne` 有多个账号, 那么在使用 `Scheduler` 等特性时你就需要提前通过 `Ariadne.config` 配置好默认账号.

如果你的 `Ariadne` 只有一个账号, 那么 `Ariadne` 就会自动设置默认账号.

## 配置连接

`Ariadne` 并不只支持 `HTTP` 与 `WebSocket` 的正向连接，也不一定需要你的 `mirai-api-http` 在 `http://localhost:8080` 提供服务.

从 [`graia.ariadne.connection.config`][graia.ariadne.connection.config] 导入对应的 `Config` 类, 实例化后
将其作为尾随的位置参数填入 [`config`][graia.ariadne.connection.config.config] 函数即可配置.

比如:

```python
from graia.ariadne.entry import HttpClientConfig, WebsocketClientConfig, Ariadne

Ariadne(
    12345678, # 账号
    "VerifyKey", # 验证钥
    HttpClientConfig("http://localhost:21476"), # HTTP 配置
    WebsocketClientConfig # WebSocket 配置, 使用了默认的 `http://localhost:8080`
)
```

!!! note "提示"

    如果你添加了额外的参数则默认配置会被清除,
    即仅传入 `HttpClientConfig` 时 `Ariadne` 仅会通过正向 HTTP 连接.

!!! example "又及"

    默认情况下 [`HttpServerConfig`][graia.ariadne.connection.config.HttpServerConfig] 和 [`WebsocketServerConfig`][graia.ariadne.connection.config.WebsocketServerConfig]
    使用的是 `aiohttp` 的实现, 如果你在 `Launart` 上安装了 `StarletteService` 和 `UvicornService` 则会自动切换.
