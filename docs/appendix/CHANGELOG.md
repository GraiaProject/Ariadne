# 更改日志

## 0.6.16

### 新增

现在可以通过 `graia.ariadne.util.interrupt` 中的 `FunctionWaiter` 与 `EventWaiter`
更方便地使用中断(Interrupt)了. ([使用说明](../advance/broadcast/interrupt.md))

现在可以使用 `graia.ariadne.util.validator` 中的
`CertainGroup`、`CertainFriend`、`CertainMember` 与 `Quoting`
作为 `decorator` 用于指定 **必须由哪个群/好友/群成员** 或 **必须回复指定消息(使用消息ID)** 才能触发.

新增 `FuzzyMatch`. (模糊匹配，更推荐使用 `FuzzyDispatcher`，[使用说明](../basic/base-parser.md))

可以在 `Group`、`Member`、`Friend` 与 `Stranger` 之间使用 `==` 运算符判断是否为同一对象了.

### 改进

提高了 `Adapter` 的稳定性.

优化了 `Twilight` 的帮助字符串生成器. (如: 可自定义格式化帮助字符串的格式)

优化了 `Ariadne` 的生命周期的实现.

### 修复

修复了 `GroupNameChangeEvent` 与 `GroupEntranceAnnouncementChangeEvent` 的字段类型.

## 0.6.15

修复 `Ariadne` `Adapter` 过早设置 `connected` 旗标的 bug. ([#131](https://github.com/GraiaProject/Ariadne/issues/131))

提升了 `CoolDown` 的代码补全.

## 0.6.14

修复 `Python 3.8` 兼容性 (#130)

支持风控日志警告.

补充 `graia.ariadne.entry` 导出.

## 0.6.13

将 `WildcardMatch` 行为更换为以前的行为 (依照是否有内容判断 `matched` 字段).

修复 `AriadneBaseModel.dict` 会引发 `Deprecated` 的错误.

## 0.6.12

支持 `NudgeEvent` 接收 `Union[Friend, Group]` 来获取戳一戳位置.

修复 `get_running`.

## 0.6.11

修复 `MentionMe`, 优化了 `Adapter` 性能.

更新了 `API 文档`.

## 0.6.10

移除弃用的 `getMemberInfo`: 请改用 `getMember`.

修复了自动重连.

## 0.6.9

修复 #122

## 0.6.8

支持了 `registerCommand` `executeCommand` `CommandExecuted` 相关的 API 与事件.

修复了 `getUserProfile`.

修复了仅使用 Websocket 的适配器的错误行为.

!!! warning "弃用"

    `getMemberInfo` 已被弃用，请使用 `getMember` 替代, 将在 `0.6.10` 或更高版本中移除。

## 0.6.7

修复 `Alconna`.

修复 `getFileIterator` 与 `getAnnouncementIterator`.

## 0.6.6

为 `Twilight` 使用泛型参数分发.

支持使用 `Compose` 来组合基本的 `Decorator`.

修复直接从 `typing` 导入 `Annotated` 导致的 `Python 3.8` 无法使用.

修复一些地方错误的 `get_running` 导入.

修复 `publishAnnouncement` 中未对 `base64` 进行解码的问题.

移除 `Commander` 的 `assert` 辅助函数使用.

将 `graia.ariadne.util.helper.CoolDown` 改为 `graia.ariadne.util.cooldown.CoolDown`.

## 0.6.5

更改 `Alconna` 适应 `0.7.2` 改变 (#118) (@RF-Tar-Railt)

## 0.6.4

为所有事件启用泛型参数分发支持.

修复 `CoolDown` (#117) (@Redlnn)

## 0.6.3

### 修复

`Mention` 与 `MentionMe` 实现.

`Twilight` 对 `ArgumentMatch` 是否匹配判断错误.

### 改进

允许 `Group.getAvatar` 使用 `cover` 参数名获取其他封面. (#116) (@SocialSisterYi)

支持 `twilight.Match` 使用位移符号.

允许 `Ariadne.create` 尝试递归创建对象.

`Twilight` 更好的帮助生成.

更新 `Alconna` 至 `0.7+` 并添加 `skip_for_unmatch` 参数. (#115)

## 0.6.2

### 添加

增加 `graia.ariadne.util.helper.CoolDown` 工具类.

### 改进

`ReverseAdapter` 现在会在 5s 内退出失败后强制退出.

## 0.6.1

### 改动

重命名原来的 `CombinedAdapter` 为 `ComposeForwardAdapter`

### 添加

增加了 `ReverseAdapter`, 基于服务器的适配器. ([#114](https://github.com/GraiaProject/Ariadne/issues/114))

### 修复

`WebsocketAdapter.call_api` 无法正常运作

`Twilight.from_command` ([#112](https://github.com/GraiaProject/Ariadne/pull/112))

`Alconna` 相关 ([#111](https://github.com/GraiaProject/Ariadne/pull/111))

## 0.6.0

!!! warning "警告"

    `0.6.0` Twilight API 有重大变动, 为不兼容更新

### 破坏性变动

重构 `Twilight` ([#106](https://github.com/GraiaProject/Ariadne/issues/106))

将 `Ariadne.get_running` 移至 `graia.ariadne` 命名空间.

`asMappingString` 与 `fromMappingString` 现在仅供内部使用.

### 添加

完成新版 `Mirai API HTTP` 支持: ([#102](https://github.com/GraiaProject/Ariadne/issues/102))

支持[群公告接口](https://github.com/project-mirai/mirai-api-http/blob/master/docs/api/API.md#%E7%BE%A4%E5%85%AC%E5%91%8A)

支持 `getFileIterator` 与 `getAnnouncementIterator` 用于遍历文件信息与群公告.

添加 `MatchTemplate` 用于消息链模板匹配.

### 改进

`MessageChain.download_binary` 会返回自身以支持链式调用.

`MessageChain` 与 `Element` 都完整支持相加操作.

`Twilight` 性能大幅度提升.

提高消息日志记录的优先级. ([#107](https://github.com/GraiaProject/Ariadne/issues/107))

### 修复

`AlconnaDispatcher` 无法运作.

`Mention` 无法运作.

未将 `MiddlewareDispatcher` 注入导致无法处理 `ExceptionThrowed`.

文件上传时文件名会被编码 ([#108](https://github.com/GraiaProject/Ariadne/issues/108))

### 删除

`Literature` 消息链解析器.

`Component` 消息链工具.

## 0.5.3

### 添加

完成新版 `Mirai API HTTP` 支持: ([#102](https://github.com/GraiaProject/Ariadne/issues/102))

- 添加 `ActiveMessage` 系列主动事件:
`ActiveFriendMessage` `ActiveGroupMessage` `ActiveTempMessage`
及其对应 `SyncMessage`.

- 添加 `MarketFace` 元素类型 (用户无法发送).

- 添加 `getUserProfile` API (未 merge).

在 `Member` `Group` `Friend` 上添加 `getAvatar` API.

`Ariadne.get_running` API 用于替代旧的 `xxx_ctx.get()`.

`Commander` 的 `Saya` 支持.

### 修复

`Broadcast` 的 `Decorator` 无法正常运作.

更好的多账号支持.

## 0.5.2

### 添加

实现 `MessageChain.replace` ([#97](https://github.com/GraiaProject/Ariadne/issues/97))

### 修复

`Commander` 行为错误, 性能过低.

`0.5.1` 对 `Broadcast Control` `v0.15` 的适配不完善.

部分消息链处理器因 `asMappingString` API 变动损坏.

### 删除

`Twilight` 中的 `ArgumentMatch` 若是位置匹配现在会引发异常.

删除 `graia.ariadne.message.parser.pattern` 模块.

## 0.5.1

### 添加

实现 `Ariadne Commander`. ([#70](https://github.com/GraiaProject/Ariadne/issues/70) [#76](https://github.com/GraiaProject/Ariadne/issues/76) [#80](https://github.com/GraiaProject/Ariadne/issues/80) [#82](https://github.com/GraiaProject/Ariadne/issues/82) [#86](https://github.com/GraiaProject/Ariadne/issues/86))

`Ariadne.sendMessage` 支持通过 `action` 自定义行为. ([#75](https://github.com/GraiaProject/Ariadne/issues/75))

支持 `MessageChain[int : int]` 格式的原始切片.

支持对 `Friend` `Group` `Member` 等对象执行 `int` 以获取其 `id` 属性. 并拓展了一些方便方法.

有多个 `Member` 对象属性的事件对 `Member` 的分派 ([#81](https://github.com/GraiaProject/Ariadne/issues/81))

`Ariadne` 的操作均会引发审计事件 (Audit Event): `CallAriadneAPI`, 带有 `api_name` `args` `kwargs` 三个参数. ([#74](https://github.com/GraiaProject/Ariadne/issues/74))

`Ariadne` 收到的事件会额外引发审计事件 (Audit Event): `AriadnePostRemoteEvent`, 携带 `event` 单个参数. ([#73](https://github.com/GraiaProject/Ariadne/issues/73))

添加了 `SenderDispatcher`. ([#84](https://github.com/GraiaProject/Ariadne/pull/84))

支持对 `MemberPerm` 进行富比较操作. ([#85](https://github.com/GraiaProject/Ariadne/issues/85))

`MessageChain` 部分操作加速.

更好的 `Mirai Event` 文档字符串.

`Ariadne.recallMessage` 支持使用 `MessageChain`.

默认关闭适配器 `websocket` 日志, 更好的连接失败提示.


### 修复

`MessageChain.endswith` 的行为异常 ([#68](https://github.com/GraiaProject/Ariadne/issues/68))

消息元素中的戳一戳 (Poke) 无法发送 ([#77](https://github.com/GraiaProject/Ariadne/issues/77))

自动处理不支持的消息类型 ([#79](https://github.com/GraiaProject/Ariadne/issues/79))

`Commander` 与 `Console` 会自动解析 `dispatcher` 的 `mixin`.

修复 `BotMuteEvent` 的 `Group` 解析问题.

修复部分事件的分类错误问题.

修复不同类型子事件被同时监听时的 `Broadcast` 错误调用 `Dispatcher` 的问题 ([#83](https://github.com/GraiaProject/Ariadne/issues/83))

保证 `MessageChain` 元素对象安全性.

降低全局 `ApplicationMiddlewareDispatcher` 优先级.

支持 `Graia Broadcast v0.15` ([#88](https://github.com/GraiaProject/Ariadne/issues/88))

### 弃用

`Twilight` 中的 `ArgumentMatch` 若是位置匹配则会被静默替换为 `ParamMatch`. 在 `0.5.2` 中这样的构造方式会直接引发异常.

### 移除

移除模块 `graia.ariadne.event.network`. ( ~~因为没有人用~~ )

## 0.5.0

### 添加

- 添加了内置 `Console` ([#41](https://github.com/GraiaProject/Ariadne/issues/41))
- 添加了新的消息链解析工具—— `Alconna` ([#37](https://github.com/GraiaProject/Ariadne/issues/37))

### 改动

- 现在可以接收 `Broadcast` 与 `Adapter` 实例了
- 可以构造转发消息了
- 可以禁用 `WebsocketAdapter` 的心跳包的 log了
- `ArgumentMatch` 支持类型匹配了
- 新的启动与停止 `Ariadne` 的方法
- `Adapter` 的停止过程更安全了 ([#30](https://github.com/GraiaProject/Ariadne/issues/30), [#65](https://github.com/GraiaProject/Ariadne/issues/65))
- 可以更好的获取实例所辖账号了([#31](https://github.com/GraiaProject/Ariadne/issues/31))
- 提升 `Twilight` 的性能 ([#44](https://github.com/GraiaProject/Ariadne/issues/44))
- `sendNudge`（发送戳一戳）现在更灵活了 ([#47](https://github.com/GraiaProject/Ariadne/issues/47))
- 向 `ParallelExecutor` 添加 `to_thread` 与 `to_process` ([#50](https://github.com/GraiaProject/Ariadne/issues/50))
- 将 `graia.ariadne.message.parser.pattern` 的所有内容移到 `Literature` 与 `Twilight` 模块里 ([#53](https://github.com/GraiaProject/Ariadne/issues/53))
- 添加 `ParamMatch` 并拓展 `Sparkle.__getitem__` ([#57](https://github.com/GraiaProject/Ariadne/issues/57))
- 添加 `space` 参数与 `SpacePolicy` 以替代 `preserve_space` ([#59](https://github.com/GraiaProject/Ariadne/issues/59))
- `Ariadne.uploadFile` 支持指定文件名 ([#66](https://github.com/GraiaProject/Ariadne/issues/66))

### 修复

- `Ariadne.uploadImage` 出错 ([#43](https://github.com/GraiaProject/Ariadne/issues/43))
- `async_exec` 相关 ([#50](https://github.com/GraiaProject/Ariadne/issues/50))
- `Queue.get` 任务退出时没被 `await` ([#51](https://github.com/GraiaProject/Ariadne/issues/51))
- 自动用 `repr()` 转义 log 中发送的消息 ([#58](https://github.com/GraiaProject/Ariadne/issues/58))
- `Adapter` 不会自动重连 ([#60](https://github.com/GraiaProject/Ariadne/issues/60))
- `NudgeEvent` 接收陌生人的戳一戳出错 ([#63](https://github.com/GraiaProject/Ariadne/issues/63))

### Breaking Changes

- `Ariadne.request_stop` -> `Ariadne.stop`
- `Ariadne.wait_for_stop` -> `Ariadne.join`
