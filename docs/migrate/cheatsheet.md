# 变动的 API 一览

!!! warning "Working In Progress"

    本部分急需改进, 欢迎 `Graia Application` 用户踊跃参与!

# 改动

本部分阐述了可部分或全部与原有 API 等价的变动.

## 模块

`graia-template` -> `graia.ariadne.message.formatter` (用法不同)

## 方法

## GraiaMiraiApplication

`GraiaMiraiApplication.kick` -> `Ariadne.kick_member`

`GraiaMiraiApplication.mute` -> `Ariadne.mute_member`

`GraiaMiraiApplication.unmute` -> `Ariadne.unmute_member`

`GraiaMiraiApplication.nudge` -> `Ariadne.send_nudge`

## MessageChain

-   `MessageChain` 实例化方式更丰富了.

-   `MessageChain.plus` -> `MessageChain.extend`

-   `MessageChain.plusWith` -> `MessageChain.__add__` 或 `MessageChain.extend(..., copy=True)`

-   `MessageChain.asSerializationString` -> `MessageChain.as_persistent_string` (格式不同)

-   `MessageChain.fromSerializationString` -> `MessageChain.from_persistent_string` (格式不同)

-   `MessageChain.asMerged` -> `MessageChain.merge()`

-   `MessageChain.onlyHas` -> `MessageChain.only`

-   `MessageChain.hasText` -> `MessageChain.has` (接受多种形式)

-   `MessageChain.join` -> `sum(message_chains)` (`MessageChain` 可直接相加)

### Element

#### 多媒体元素

- `MultimediaElement.http_to_bytes` -> `MultimediaElement.get_bytes`

# 移除

本部分阐述了被删除的 API.

## 模块

-   `graia.application.message.elements.internal`

-   `graia.application.message.elements.external`

-   `graia.application.message.parser.kanata`: 请用 `graia.ariadne.message.parser.twilight`.

## 方法

### MessageChain

-   `MessageChain.isImmutable`

-   `MessageChain.asImmutable`

-   `MessageChain.asMutable`

-   `MessageChain.isSendable`

-   `MessageChain.asHypertext`

# 添加

本部分阐述了新增的 API.

## 方法

### MessageChain

-   `MessageChain.download_binary`

-   `MessageChain.index`

-   `MessageChain.count`

-   `MessageChain.removeprefix`

-   `MessageChain.removesuffix`

-   `MessageChain.merge`

-   `MessageChain.extend`

-   `MessageChain.append`

-   `MessageChain.copy`

-   `MessageChain.download_binary`

-   支持以下魔术方法:
    -   `__add__` 与 `__iadd__`

    -   `__mul__` 与 `__imul__`

    -   `__len__`

    -   增强过的 `__contains__`

    -   增强过的 `__getitem__`

### Element

#### 多媒体元素

- `MultimediaElement.uuid`
