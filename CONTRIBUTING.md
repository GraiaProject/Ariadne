# Contribute to Ariadne

**在此为所有向 `Graia Project` 作出贡献, 为社区添砖加瓦的每位开发者/使用者表示衷心的感谢, 你们的支持就是我们开发的动力.**

`Graia Project` 下所有项目都欢迎任何环抱开源精神的贡献者.
而本文档则提到了我们能想到的在贡献本项目时你应该/不应该做的事.

你可以通过以下方式向本项目 `Ariadne` 作出贡献:

 - 协助寻找 BUG 
 - 协助修复已发现的/潜在的 BUG
 - 为本项目开发新特性/功能(请先通过 Github Issue 向我们提出建议 ~~然后我们可能会推出官方的方案~~ )
 - 添加非必要的功能支持
 - 修改异常的代码行为
 - 在 Github Issue 里写关于某个文档尚未提到的特性的使用方法探索
 - 帮助撰写 [Guide](guide)

注意事项:
 - 尽量别引入新的库
 - 使用 black 与 isort 进行格式化. 尽量符合 [`PEP 8`](https://www.python.org/dev/peps/pep-0008/).
 - 如果需要测试文件, 放在 `test` 文件夹下. (涉及到的资源请以 `*.temp` 命名, 防止 git 跟踪.)
 - 最好是所有声明的变量都加上类型注解.
 - 使用 `poetry` 管理环境.
 - 别修改 `setup.py`, 使用 `poetry`.
 - 如果涉及到修改有关 `mirai-api-http` 交互的部分, 请先测试下, 并在 PR 里标出你所使用的版本.
 - 看不懂的东西请别改...
 - `docstring` 用 Google Style.
 - 类名与方法名尽量符合 [`PEP 8`](https://www.python.org/dev/peps/pep-0008/).
 - 需要添加一个实用函数请在 `graia.araidne.util` 这个模块下面加
