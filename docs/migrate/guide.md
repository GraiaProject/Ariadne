# 概述

最大的更改: `graia.application` -> `graia.ariadne`

## 导入

你仍然可以从 `graia.ariadne.entry` 导入所有东西, 但是有所不同:

-   与消息有关的 (消息链, 元素, 处理器) 等放在 `graia.ariadne.entry.message`.

-   所有事件 (包括消息事件) 都放在 `graia.ariadne.entry.event`.

此外, `Ariadne` 的模块名都是单数形式的 (`utilles -> util`, `elements -> element`)

## 消息相关

没有 `InternalElement`, `ExternalElement`, `ShadowElement` 之分, 现在所有元素都继承自 `Element`.

`MessageChain` 均为可变对象.

无法将消息链转换成 `Mirai Code`, 取而代之的是持久化字符串 `PersistentString`.

`MessageChain` 的方法得到极大的拓展 (更好的 `create`, `__add__` 与 `__mul__` 支持等)

此外, `__contains__` (`has`) 支持子消息链检测.

`Kanata` 被 `Twilight` 取代了, `Template` 被用法稍有不同的 `Formatter` 替代.

### 消息元素

元素不再分为 `Internal` `External` 与 `Shadow` 三态. 对应的, `Image_LocalFile` `Voice_LocalFile` **等** 类型被删除了.

多媒体元素实例化签名更丰富, 可接受 `bytes` `url` `path` `id` `base64` 等.

所以对于 `Image.fromLocalFile` 等类方法, 直接实例化即可.

## 与主实例交互

统一所有方法为 谓词 + 名词 形式并且为 `snake_case` (如 `kick` -> `kick_member`,`mute` -> `mute_member`...)

`launch_blocking()` 会自动捕获一个 `KeyboardInterrupt` 并主动停止实例.
