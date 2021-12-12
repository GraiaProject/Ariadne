# FAQ - 常见问答

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
