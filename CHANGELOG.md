# 更改日志

## 未发布的更新

### 修复

- 通过 `creart` 获得 `asyncio.AbstractEventLoop`
- 提高 graia 基建依赖版本

## 0.11.6

### 修复

- 暂时对依赖版本进行了更严格的限制。
- 修复了 `Ariadne.get_member` 错误将 `Member` 缓存为 `Group` 的问题。

## 0.11.5

### 修复

`Safe` 发送动作仅会捕获部分异常并进行重试，而非全部捕获。([#234](https://github.com/GraiaProject/Ariadne/issues/234))

## 0.11.4

### 修复

- 修复了 `Ariadne.send_message` 在 `quote = True` 时永远会引发 `TypeError` 的问题 ([#229](https://github.com/GraiaProject/Ariadne/issues/229))
- 使用 HttpServer 时，传入的 qq header 有误会返回 403 而非引发 500 Internal Error ([#230](https://github.com/GraiaProject/Ariadne/issues/230))

## 0.11.3

### 修复

修复了在 `Mirai` 登陆完成前 `Mirai API HTTP` 发起反向 WebSocket 连接会导致连接挂起的问题。

## 0.11.2

### 修复

修复了 `NoneDispatcher` 被缓存时，会激进地为所有 `Optional` 值赋值为 `None` 的问题。
（这修复了 `Optional[Quote]` 等值的分发）

## 0.11.1

### 修复

修复了 `Commander` 无法正确处理 `PropagationCancelled` 特殊异常的问题。

## 0.11.0

### 新增

`MemberJoinRequestEvent.invitor_id` 邀请申请人入群者

`GroupConfig.mute_all` 是否在全员禁言

`Ariadne.kick_member(block: bool = False)` 是否不再接受该成员加群申请

`Ariadne.get_member_list(cache: bool = True)` 是否使用缓存的群员列表

`DisplayStrategy`, `Forward(display: DisplayStrategy | None = None)` 转发消息的预览策略

`NudgeEvent.subject` 戳一戳上下文

`AccountConnectionFail` 生命周期事件，在连接错误时被触发（断开连接/连接失败）

### 改进

带 action 调用 `Ariadne.send_friend_message()` 和 `Ariadne.send_group_message()` 时使用缓存的 `Friend` 和 `Group` 对象。

### 修复

修复了 `Ariadne.send_message()` 向未知目标发送消息时报错的问题。

修复了 `Forward` 为空时发送失败的问题。

### 弃用

弃用 `ForwardNode.message_id`。
它从来都不是 `ForwardNode` 显式声明的参数，在接收到的消息中一直为 `None`。
想复用接收到的消息，请直接将 `MessageEvent` 作为 `Forward` 的参数。

弃用 `NudgeEvent.context_type`, `NudgeEvent.origin_subject_info`, `NudgeEvent.friend_id` 和 `NudgeEvent.group_id`

## 0.10.3

### 修复

修复了 `Launart 0.6.2` 兼容性。([#209](https://github.com/GraiaProject/Ariadne/issues/209))

## 0.10.2

### 修复

引入 `Scheduler 0.1.1` 作为依赖。

增加了包的元数据不存在时的应对方案。

## 0.10.1

### 修复

修复了 [对好友，群，群成员和版本等信息使用缓存 (@ProgramRipper)](#090) 带来的内存泄露问题，此问题波及 0.9.0~0.10.0 的所有版本，强烈建议升级到此版本。

## 0.10.0

### 修复

自行实现 `class_property` 以适应 `Python 3.11` 的更改。

修复了预览版 PyPI 包会导致更新检查失败的问题。

修复了 `Ariadne.make_directory` 的错误参数。

### 新增

支持分派 `Quote` 和 `launart.ExportInterface`。

现在 `Ariadne.default_action` 会作用于所有发送方法。

所有发送方法都可以传入 `action` 参数。

没有配置账号时会引发 `ValueError`。

丰富了 `CoolDown` 的功能。

向 `Ariadne.send_message` 的 `quote` 传入错误参数时会引发 `TypeError`。

### 更改

现在会使用 30s 一次的自动心跳包。这也许能解决长时间收不到消息导致的伪断连问题。

将 `RequestEvent.requestId` 改为 `RequestEvent.request_id` （虽然没有人用这个）

现在将全部改用 “实验性消息链” 的行为。（`Source` `Quote` 作为 `MessageEvent` 的属性）

`Source` 与 `Quote` 不再是 `Element` 的子类。

### 移除

删除了自 `0.9` 以来弃用的属性。

现在传入 `MessageChain` 作为 `quote` 对象会报错。

## 0.9.8

### 修复

修复了 `BotLeaveEventKick`, `BotLeaveEventDisband`, `GroupRecallEvent` 和 `GroupNameChangeEvent` 的 `Dispatcher` 拼写错误.

补充了 `ExceptionThrown` 和 `EventExceptionThrown` 的一站式导入.

## 0.9.7

### 修复

修复了发送的 `MessageChain` 带有旧 `MessageChain` 的不可发送的 Element 的 bug. (@ProgramRipper)

修复了 `recall_message` 的 `target` 相关问题。(@ProgramRipper)

修复了 `ResultValue` 作为 `Derive` 使用时的实现问题。(@BlueGlassBlock)

## 0.9.6

### 修复

修复了 `graia.ariadne.message.parser.twilight.ResultValue`.

修复了使用 Derive 特性时可能的参数检查 bug.

### 更新

支持 `RegexGroup` 作为 Decorator 使用.

`MatchRegex` 现在默认统一为 `fullmatch`.

## 0.9.5

### 修复

修复了 `graia.ariadne.connection.config.from_obj` 的 bug.

维持 console dispatcher 的向后兼容性.

### 弃用

`Quote` 与 `Source` 在 `0.10.0` 将成为 `MessageEvent.quote` 与 `MessageEvent.source` 而不是 `MessageChain[1]` 与 `MessageChain[0]`.

当然，`MessageChain.get_first(Quote)` 与 `MessageChain.get_first(Source)` 到时候也会报错.

同时，`MessageChain.startswith` 的行为将会变得 **符合直觉**.

相应的弃用警告已经发出.

如果你想维持稳定行为，请迁移使用 `from graia.ariadne.message.exp import MessageChain as ExpMessageChain` 作为 **分发类型标注**.

构造时原有消息链不受影响.

## 0.9.4

### 修复

删除了内部的过时用法.

修复了 `Forward` 元素的 `as_persistent_string`. (#195)

## 0.9.3

### 修复

修复了 Python 3.9 以下的类型标注问题.

修复了内部 Dispatcher 的一个用法.

## 0.9.2

### 依赖

现在 `Ariadne` 依赖于 `pydantic~=1.9`. (@BlueGlassBlock)

### 新增

`MessageEvent` 与 `ActiveMessage` 添加 `source` 与 `quote` 属性.

实验性 API: `graia.ariadne.message.exp.MessageChain`

使用此类型进行标注时会将前导 `Source` 与 `Quote` 去除.
## 0.9.1

### 修复

修复了 `GroupMessage` dispatcher 错误 (@BlueGlassBlock)

## 0.9.0

适配 `mirai-api-http 2.6.0+` (@ProgramRipper)

### 修复

适配 `Amnesia 0.6.0+` (@BlueGlassBlock)

修复了 `NoneDispatcher` (@ProgramRipper)


### 增强

`Formatter` 现在可以使用相对完整的格式化微型语言 (@BlueGlassBlock)

对好友，群，群成员和版本等信息使用缓存 (@ProgramRipper)

使用 `Amnesia` 内建的 `MessageChain` 方法 (@BlueGlassBlock)

### 新增

`{MessageEvent|ActiveMessage}` 的 `id` 字段. (@ProgramRipper)

`get_roaming_message` 用于获取漫游消息. （@ProgramRipper)

`get_bot_list` 用于获取所有登录的账号. (@ProgramRipper)

`Image` 和 `FlashImage` 的新增元信息字段. (@ProgramRipper)

### 弃用

`BotMessage` 被标记为弃用. 它将在 `0.10.0` 中被移除. (@ProgramRipper)

弃用了 `MessageChain.{zip|unzip|find_sub_chain}` (@BlueGlassBlock)

`set_essence` `get_message_from_id` `recall_message` 不带上下文（直接使用 `int` / `Source`) 进行调用会触发警告.

### 移除

移除了 `as_display` 等弃用方法. (@BlueGlassBlock)

## 0.8.3

### 修复

修复了 `Ariadne.get_version`, `Ariadne.file_remove` 调用时报错的问题

修复了遥测 SSL 版本过低的问题

修复了 `Poke` 无法解析未知 Poke 类型的问题

## 0.8.2

### 修复

适配 `Amnesia 0.5.5+`.

修复了同时使用 http 和 webhook 通讯时无法调用 api 的问题

### 回退

回退了 `0.8.0` 中的改进: [使用 `url` 作为基于 `Path` 的 `MultimediaElement` 的实现](#080).

## 0.8.1

### 修复

修复了 `graia.ariadne.entry` 的部分错误与缺失.

## 0.8.0

### 改进

`MatchTemplate` 现在支持 `Element` 类的 `Union`.

`Ariadne.launch_blocking` 支持自定义停止信号.

自动忽略结束时未完成的 Amnesia transport 导致的 `CancelledError`.

使用 `url` 作为基于 `Path` 的 `MultimediaElement` 的实现.

### 修复

修复 `HttpServerInfo` 缺失 `verify_key` 导致 `TypeError` 的问题.

修复 interrupt util 的内置 `wait` 问题.

### 移除

移除了弃用的方法名转换和部分事件属性名.

## 0.7.18

### 修复

修复了 `Commander` 无法正确识别可选参数的问题.

修复了项目 `Classifier` 不正常的问题.

## 0.7.17

### 其他

改用 [`pdm`](https://github.com/pdm-project/pdm) 管理项目依赖.

### 修复

修复 `ForwardNode` 的序列化问题.

修复了 `creart` 导入顺序的问题.

## 0.7.16

### 改进

更改了遥测的显示顺序, 改进了显示方式.

`model.relationship` 下的 `Model` 不再是内部类.

支持 `Forward` 转发消息的序列化.

支持直接使用 `MessageEvent` 作为片段构造转发消息.

### 新增

添加 `AnnotationWaiter`.

可以在 `MatchRegex` 和 `Twilight` 中使用 `RegexGroup` 来提取正则表达式中的组.

### 修复

修复了 `WebsocketServerConnection` 不会自动注入服务器依赖的问题.

修复了 `Saya util`.

## 0.7.15

### 新增

添加 `BotLeaveGroupDisband` 事件. (project-mirai/mirai-api-http#585)

### 改进

`Commander` 现在在尾部支持多个可选的 `Slot`. (#181)

`Twilight` 现在可以较好地分派带有泛型的 `MatchResult`.
### 弃用

使用 `creart` 替代 `Ariadne.create`.

自定义 `Broadcast` 与事件循环无效，并且会引发警告.

### 移除

移除了弃用的 `graia.ariadne.message.parser.alconna` 模块, 请使用 `arclet.alconna.graia`

## 0.7.14

### 修复

修复了 `AttrConvertMixin`.

修复了 `Commander` dispatcher 优先级错误的 bug.

### 改进

Saya util 支持基于事件的优先级.

## 0.7.13

### 修复

修复了 `datetime` 无法被正确序列化的 bug.

### 改进

现在检查更新放在清理任务中执行.

重新实现了 `Commander` (#179) (@BlueGlassBlock)

支持使用 `types.UnionType` (#178) (@ProgramRipper)

重新实现了 saya util.

## 0.7.12

### 修复

修复了 `datetime` 无法被正确序列化的 bug.

### 修改

将公告对象中的 `camelCase` 属性修正为 `snake_case`.

现在 `Websocket` 连接的报错更直观了.

## 0.7.11

### 修复

修复了 `get_avatar` 无法使用的问题.

## 0.7.10

### 修改

将消息元素中的 `camelCase` 属性修正为 `snake_case`.

### 修复

修复了遥测的 bug.

## 0.7.9

### 新增

增加了 `graia.ariadne.util.saya` 模块。

重新加入了 `Ariadne` 的启动遥测.

### 修复

修复 `Elizabeth` 的 `AiohttpClientInterface` 未初始化的问题.

修复了 `datetime.datetime` 的序列化问题.

## 0.7.8

### 修复

修复了 `graia-application-mirai` 可以和 `graia-ariadne` 同时存在的 bug.

`CommanderBehaviour` 和 `ConsoleBehaviour` 适配新的 `Saya`.

### 改进

更好的 `MessageChain` 初始化实现.

`send_friend_message` `send_group_message` `send_temp_message` 现在都直接支持 `MessageContainer` 类型.

允许通过 `extra` 参数方便地自定义 `LogConfig` 的事件捕获类型.

优化了默认日志格式.

### 增加

`graia.ariadne.connection.config.from_obj` 支持使用两种方式直接从配置构造 `Ariadne` 对象.

## 0.7.7

### 改进

更好的事件循环异常处理器实现.

### 修复

修复了 `twilight.ResultValue`.

修复 `Ariadne.upload_xxx`

修复 `internal_cls` 过于严格的 bug

## 0.7.6

### 更改

在 `Ariadne` 清理时自动停止所有 `Scheduler` 和 `Broadcast` 任务.

修复了 `MemberInfo` 的签名.

## 0.7.5

### 修复

`MessageChain` 创建时不会因为含有特殊元素而报错.

## 0.7.4

### 修复

`Broadcast` 内部运行产生的正常异常不会被记录.

### 新增

添加 `twilight.ForceResult`，让 `twilight.ResultValue` 支持 `Derive`.

## 0.7.3

### 修复

修复了不能通过 `Ariadne.stop` 正确停止的问题.

### 修改

将 `model` 中的 `camelCase` 属性修正为 `snake_case`.

## 0.7.2

### 修改

现在被弃用的方法仅在运行时可用.

## 0.7.1

### 改进

`Ariadne` 会智能注入日志和异常处理元件, 就像 `0.6.x` 一样.

### 修复

修复了 `MessageChain` 的 MRO 问题.

## 0.7.0

### 新增

支持 `Twilight` 使用 `predicate` 进行先行条件判定 (#167)

`DetectPrefix` 与 `DetectSuffix` 支持多个前后缀匹配 (#149) (@luoxhei)

`MentionMe` 支持多种匹配方式.

提供 Broadcast 中 `Derive` 风格的消息链匹配器支持.

添加了 `py.typed` 文件.

### 修改

全面推荐使用 `snake_case` 的方法和事件属性，清除了一批无用方法函数.

使用 `Amnesia` 作为后端. (#156)

修复内置的 Waiter (#164)


## 0.6.16

### 新增

现在可以通过 `graia.ariadne.util.interrupt` 中的 `FunctionWaiter` 与 `EventWaiter`
更方便地使用中断(Interrupt)了. ([使用说明](../advance/broadcast/interrupt.md))

现在可以使用 `graia.ariadne.util.validator` 中的
`CertainGroup`、`CertainFriend`、`CertainMember` 与 `Quoting`
作为 `decorator` 用于指定 **必须由哪个群/好友/群成员** 或 **必须回复指定消息(使用消息ID)** 才能触发.

新增 `FuzzyMatch`. (模糊匹配，更推荐使用 `FuzzyDispatcher`，[使用说明](../feature/base-parser.md))

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

### 弃用

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
