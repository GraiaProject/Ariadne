# 谈谈 Twilight

## 诞生

`Twilight` 诞生于 `2021.11.4` 的晚上.

你问名称来源? 文档里已经讲得很清楚了（

当时我对 `Twilight` 的定位是 `Literature` 的青春版, 不过现在她已经成为 `Kanata` 与 `Literature` 的结合体了 (而且效率更高)......

## 关于代码量

当时主代码只有 217 行.
之后在 [a3c17fd](https://github.com/GraiaProject/Ariadne/commit/a3c17fdfd02933b36dfd66dd61ff72b40b1e25b9) 的重写中, 代码量飙升至 424 行.
现在代码量在 360 行左右.

## 关于性能

其实性能很大的一个瓶颈在 `deepcopy` 的使用上.

删掉以后可以达到 22000 msg/s......

之前只有 4000 ~ 6000 msg/s, 在 [055fb26](https://github.com/GraiaProject/Ariadne/commit/055fb268b59be9dd0a7658900aa29b52313eafa3)
减少 `deepcopy` 使用并更改 `__getattribute__` 后, 现在性能有 6000 ~ 10000 msg/s 了.

其实我本来不想暴露 `check` 参数的匹配出来, 但是 `A60` 已经在代码里用上 `_check_0` 等 `private` 变量了, 所以最后我提供了一个折中方案: 通过 `__getitem__` 访问.

现在我通过 `__getattribute__` 的重载, 而非手动在新实例上 `setattr`, 让代码逻辑清晰了不少.

> BlueGlassBlock 2021/12/10
