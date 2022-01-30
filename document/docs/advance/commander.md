# Commander - 便捷的命令触发系统

## 在开始之前

现在 `Ariadne` 的命令解析实现方式异常丰富.

- 最简单的指令解析: `DetectPrefix` 与 `DetectSuffix`, 看 [上一章](./base-parser.md)

- 最简洁易用 / 基于 `pydantic` `BaseModel` 的指令处理器: `Commander`

- 基于正则表达式的解析 / 容错性高且易于编写的处理器: [`Twilight`](./twilight.md)

- 支持子命令解析 / 基于 dict 的高度定制解析: [`Alconna`](./alconna/quickstart.md)

按照你的需求, 选择最适合你的处理器.

## 开始使用

!!! warning "施工中"