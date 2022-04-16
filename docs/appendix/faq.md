# FAQ - 常见问答

## 如何正确的截取日志？

> Ariadne 费尽心思用 loguru 的彩色日志不是没有理由的......

`Ariadne` 日志中的报错第一行与最后一行是最重要的.

第一行通常为 日期 + 时间 + 红色的 `ERROR` + 红色的异常说明.

最后一行通常为 红色的 `XXXError` 或 `XXXException` 之类的, 再跟着白色的说明文字.

如果能用长截图之类的同时截完当然最好, 如果做不到请优先最后一行 (及其之前的异常回溯).


## 为什么收不到 xxx 事件?

请检查 `Mirai Console` 的配置, 你账号的 `PROTOCOL` (登录协议) 影响接收事件的类型. 这不是 `Ariadne` 的问题.

`NugetEvent` 需要 `Mirai` 的登录协议是 `ANDROID_PHONE/IPAD/MACOS` 中的一种

`ANDROID_PAD/ANDROID_WATCH` 协议由于腾讯服务器原因并不能接受 `NugetEvent`.

## 为什么不像 Application 一样支持 Mirai Code?

`Ariadne` 只支持构造 `Mirai Code` 而无法转换, 是因为我们不想鼓励用户先转换成 `Mirai Code`, 之后再对文本化元素进行处理.

如果你喜欢这种风格, `OneBot` 系列可能更适合你.

## 文档里怎么没有 xxx 的介绍?

`Ariadne` 是一个非常庞大的框架, 有许许多多的方法与函数, 自然无法面面俱到.

目前 `Ariadne` 的 `API 文档` 已经支持搜索功能, 你可以搜索自己想要的功能, 或者利用 `GitHub` 搜索源码.

如果你说的是 `HTTPAdapter` 与 `WebsocketAdapter` 的话, 因为 `Ariadne` 重点目前不在这里, 所以并没有怎么动 (而且可能有潜在 bug)...

## 多媒体元素的 get_bytes 方法为什么会存储 base64 属性?

你可能会有这个迷惑:

```py
img = Image(url=...)
await img.get_bytes()
assert img.base64 is not None
```

这是正常且符合设计的, 因为:

-   这个设计加速了后续的 `get_bytes` 操作.
-   `url` 优先级高于 `base64`, 不会对发送产生任何影响.
-   可以保证 `asPersistentString` 完整存储了图片数据, 以防止不可靠 `url` 影响.

可能后续会添加一个 `remove_url` 的仅关键字参数.

## TROUBLESHOOT - 常见故障排查

> 本部分用于排查常见用户错误.

### TimeoutError: Unable to connect to mirai-api-http. Configuration Problem?

请检查：

1. mirai-console 是否成功登录账号

2. mirai-api-http 是否正确配置 (启用 `HTTP` 与 `Websocket` 适配器)

3. `Python` 版本 (3.8 以上)

4. `Ariadne` 版本是否为最新 (![PyPI](https://img.shields.io/pypi/v/graia-ariadne?label=%20))

5. 其他 `Graia Project` 相关的库是否为最新 (e.g. `graia-saya` `graia-scheduler`)

6. `Ariadne` 配置是否与 `mirai-api-http` 相同. (包括 QQ 号，地址和验证密钥)

### 收不到消息，且控制台显示 `Failed to send message, your account may be blocked.`

你的账号可能被 **风控** 了. 请等待几天后再试.

### MCL 显示 `Cannot download package "net.mamoe:mirai-api-http"`

如果你的 MCL 显示以下错误输出:

```text
[INFO] Verifying "net.mamoe:mirai-api-http" v2.5.0
[ERROR] "net.mamoe:mirai-api-http" is corrupted.
[ERROR] Cannot download package "net.mamoe:mirai-api-http"
[ERROR] The local file "net.mamoe:mirai-api-http" is still corrupted, please check the network.
```

请手动下载 `mirai-api-http` 包, 并将其放置于 `MCL` 的 `plugins` 目录下.

之后便可以安全忽略这个错误. (这是因为 `mirai-api-http` 的维护者忘记发布 `mirai-api-http` 到 maven 仓库托管了, 详见 [这里](https://github.com/project-mirai/mirai-api-http/issues/557#issuecomment-1099900036))
