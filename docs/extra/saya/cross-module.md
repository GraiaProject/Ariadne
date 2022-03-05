# 跨模块使用

`Saya` 提供了很多利于跨模块调用的工具.

首先, 你需要一个 `Saya` 对象.

在 `Saya` 模块中, 使用 `saya = Saya.current()` 来获取 `Saya` 实例.

# mounts

`Saya.mounts` 是一个透明字典, 记录了外部 **挂载** 的对象.

利用 `mount` `unmount` `access` 三个方法可以访问 `Saya.mounts` 下的各个属性.

!!! warning "注意"

    请注意, `Saya.mounts` 所挂载的对象仍然遵守 `Python` 的对象赋值规则.

    ```py
    value: bool = False
    saya.mount("saya.values.value", value)
    value = True
    saya.access("saya.values.value") # 返回 False
    ```

# 跨模块的 require

在获取 `Saya` 实例后, 你自然可以 `require` 其他 `Saya` 模块了.

!!! note "提示"

    `Saya.require` 方法会自动解析重复的导入,
    保证主模块中的 `Channel` 与你 `require` 获取到的一致.

    如果你 `require` 了一个模块, 但是没有在主模块中导入,
    那它会被自动创建.

```py
saya = Saya.current()

value = saya.require("saya.other_module")
```

`value` 可以是其 `Channel` 或通过 `Channel.export` 导出的对象.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/make_ero_bot/)"
