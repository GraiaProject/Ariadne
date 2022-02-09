# 开始之前

!!! error "交涉提示"

    若你在使用的过程中遇到了问题, 请运用[提问的智慧](https://github.com/ryanhanwu/How-To-Ask-Questions-The-Smart-Way/blob/main/README-zh_CN.md).

    在与你交流的过程中, 我们有很大可能使用 [术语](./appendix/terms) 以提高交流效率.

    我们会持续追踪并修复已存在的[问题](https://github.com/GraiaProject/Ariadne/issues)并不断改进, 但是...

    我们没有任何义务回答你的问题, 这仅仅是我们的自愿行为.

## 简介

[`Ariadne`](https://github.com/GraiaProject/Ariadne) 是 [`BlueGlassBlock`](https://github.com/BlueGlassBlock) 基于
[`Graia Project`](https://github.com/GraiaProject/) 系列依赖库而编写的
**简明, 优雅** 的 聊天软件自动化框架. 其丰富而简洁的接口相信可以使开发者能更好的完成业务逻辑.

**如果认为本项目有帮助, 欢迎点一个 `Star`.**

> 接受当下, 面向未来.

## 参与开发

我们非常希望欢迎有志之士能帮助我们以各种方式完善这个项目, 若正在阅读该段文字的你正有意参与,
可前往 [GitHub 组织](https://github.com/GraiaProject/Ariadne) 了解我们的项目体系.

你可以通过以下几种方式参与进来:

-   [提交 issue](https://github.com/GraiaProject/Ariadne/issues/new/choose) _包括但不限于 bug 汇报, 新功能提案, 文档改进等._
-   发起 [Pull Requests](https://github.com/GraiaProject/Ariadne/pulls) _直接将 想法 / 修复 合并到代码库中._
-   参与 [QQ 讨论](https://jq.qq.com/?_wv=1027&k=VXp6plBD) _与开发者进行直接交流._


## 文档: 切换主题色

> 按下对应颜色即可切换.

> 默认颜色: `indigo`.

<div class="mdx-switch">
<button data-md-color-primary="red"><code>red</code></button>
<button data-md-color-primary="pink"><code>pink</code></button>
<button data-md-color-primary="purple"><code>purple</code></button>
<button data-md-color-primary="deep-purple"><code>deep purple</code></button>
<button data-md-color-primary="indigo"><code>indigo</code></button>
<button data-md-color-primary="blue"><code>blue</code></button>
<button data-md-color-primary="light-blue"><code>light blue</code></button>
<button data-md-color-primary="cyan"><code>cyan</code></button>
<button data-md-color-primary="teal"><code>teal</code></button>
<button data-md-color-primary="green"><code>green</code></button>
<button data-md-color-primary="light-green"><code>light green</code></button>
<button data-md-color-primary="lime"><code>lime</code></button>
<button data-md-color-primary="yellow"><code>yellow</code></button>
<button data-md-color-primary="amber"><code>amber</code></button>
<button data-md-color-primary="orange"><code>orange</code></button>
<button data-md-color-primary="deep-orange"><code>deep orange</code></button>
<button data-md-color-primary="brown"><code>brown</code></button>
<button data-md-color-primary="grey"><code>grey</code></button>
<button data-md-color-primary="blue-grey"><code>blue grey</code></button>
<button data-md-color-primary="black"><code>black</code></button>
<button data-md-color-primary="white"><code>white</code></button>
</div>

<script>
  var buttons = document.querySelectorAll("button[data-md-color-primary]")
  buttons.forEach(function(button) {
    button.addEventListener("click", function() {
      var attr = this.getAttribute("data-md-color-primary");
      document.body.setAttribute("data-md-color-primary", attr);
      localStorage.setItem("data-md-color-primary", attr);
      var name = document.querySelector("#__code_2 code span.l");
      name.textContent = attr.replace("-", " ");
    })
  })

</script>