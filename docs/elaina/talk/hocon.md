# 配置文件相关

在现有的, 比如 A60 的 ABot, 或是我的 Stellaium#1, 都有需要配置像是 API 密钥, 各种行为的必要...

那么, 我们先谈谈 HOCON(`Human-Optimized Config Object Notation`) 吧.

## HOCON 简介

HOCON(`Human-Optimized Config Object Notation`), 顾名思义, 是 "专为人类编写/维护等需求优化(`Human-Optimized`)" 的一种配置文件规范.

虽然这种规范比较少见(大部分都是使用的 JSON, Yaml 或是 toml), 但归功于前几年 `Sponge` 在国内的推行(现在已经很少见了...真可惜),
中文资料还是比较多的, 在这里我附上几份, 希望这些资料不要因为比特腐烂消失...

 - [(English) Informal but clear spec](https://github.com/lightbend/config/blob/master/HOCON.md)
 - [(Chinese) 非官方 HOCON 规范翻译](https://github.com/ustc-zzzz/HOCON-CN-Translation)

Python 虽然并没有像是 nodejs 一样恐怖的社区, 但在关键的时候还是靠得住的, 比如接下来要用到的 HOCON 解析库.

 - [pyhocon](https://github.com/chimpler/pyhocon)

我们接下来将使用 `pydantic.BaseSettings` 进行配置的实体类声明, 相关的文档:

 - [Settings management](https://pydantic-docs.helpmanual.io/usage/settings/)

!!! note "因为这是从我的一份古老的烂尾项目里面拿出来的遗产, 所以使用了 `camelCase`(小骆峰)"
    同样, 因为总代码量才 30 多行上下, 我懒得发包, 这里我直接附上.

我主要对 `BaseSettings.Config` 进行了修改, 使之支持了以下特性:

 - 自动转换字段名到 `spinal-case`, HOCON 里面写这种比较爽.
 - 让 `BaseSettings` 自动解析运行目录下 `config.conf`.

本模块引用了以下第三方包, 所以你需要手动 `pip install` 或者 `poetry add`.

 - `stringcase`
 - `pyhocon`
 - `pydantic`(废话.)

以下为文件 `hocon_config.py` 的内容:

```python title="hocon_config.py"
from typing import Any, Dict
from pydantic import BaseSettings, BaseConfig
import pyhocon
from pathlib import Path
import stringcase

class HoconModelConfig(BaseConfig):
    extra = "ignore"
    env_file_encoding = 'utf-8'
    env_file = "./config.conf"

    @classmethod
    def hocon_config_settings_source(cls, settings: BaseSettings) -> Dict[str, Any]:
        encoding = settings.__config__.env_file_encoding
        return dict(pyhocon.ConfigFactory.parse_string(Path(cls.env_file).read_text(encoding)))

    @classmethod
    def customise_sources(
        cls,
        init_settings,
        env_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            cls.hocon_config_settings_source,
            env_settings,
            file_secret_settings,
        )

    alias_generator = stringcase.spinalcase

class HoconConfig(BaseSettings):
    class Config(HoconModelConfig):
        pass
```

引用上面声明的 `HoconConfig` 和 `HoconModelConfig`.

```python
from hocon_config import HoconConfig, HoconModelConfig
```

!!! tip "除非你需要修改读取的文件, `HoconModelConfig` 其实可以不导入."

随便写一个类继承 `HoconConfig`, 比如 `BotConfig`:

!!! note "其实你可以在各个模块里面声明各个模块需要的 `Config`, 这样就能把与单一一个复杂, 让人头疼的配置声明转化为仅与模块所需要的相关联的, 优雅的配置."

```python
class GithubConfig(HoconConfig):
    access_token: str
    ... # 其他的字段也可以一并加上, 并且我推荐尽可能的提供默认值.
    # 比如你其实也可以把 access_token 也换成 optional, 只不过没有 access_token, github 会疯狂给你返回 429 就是了.
```

!!! warn "这里的命名方式为 `snake_case` 的字段会被转换为 `camelCase`."

其对应的配置文件格式是这样的:

```hocon
access-token: balabala
```

在用的时候直接实例化 `GithubConfig` 即可, 当然你的静态类型检查器可能会发疯, 加上 `# type: ignore` 或是 `# noqa` 可以使其闭嘴,
或者你也可以给那些空着的字段加上 `Optional` 和默认值.
这里推荐在类似 `__init__.py` 内实例化, 这样就可以在使用 Saya 导入模块时就读取配置.

!!! note "可以尝试一下反复实例化, 应该会重新加载配置, 不过你得保证程序其他部分的引用不出错."

```python
github_config = GithubConfig()  # type: ignore
```

然后直接用就好了:

```python
...

transport = AIOHTTPTransport(url="https://api.github.com/graphql", headers={
    "Authorization": f"Bearer {config.access_token}",
})

...
```

除此之外, HOCON 还支持很多震撼人心的特性, 比如:

```hocon
yggdrasil {
    token {
        availability: 8 minutes
        outdate: 10 minutes
    }
}
```

其中, `yggdrasil.token.availability` 和 `yggdrasil.token.outdate` 会被 `pyhocon` 解析为 `timedelta`.

```python
class YggdrasilTokenConfig(BaseModel):
    availability: timedelta
    outdate: timedelta

class YggdrasilConfig(HoconConfig):
    token: YggdrasilTokenConfig
```

不过, 即使你从我这篇碎碎念里面学到了怎么用 `pydantic + hocon`,
也不要冲动到直接把你的现有方式换成这样, 虽然 `hocon` 是 json 的超集(like typescript to javascript).

!!! note "或许在未来, `Avilla Config` 默认就是用的 HOCON 呢?"
