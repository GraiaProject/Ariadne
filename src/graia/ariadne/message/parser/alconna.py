from types import TracebackType
from typing import Dict, List, Optional, Union, Type, Any
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic import BaseModel
import re
from ..chain import MessageChain
from ..element import Element as MessageElement
from ...event.message import MessageEvent


class ArgumentPackage:
    name: str
    annotation: Any
    value: Any

    __slots__ = ("name", "value", "annotation")

    def __init__(self, name, annotation, value):
        self.name = name
        self.annotation = annotation
        self.value = value

    def __repr__(self):
        return "<ArgumentPackage name={0} annotation={1} value={2}".format(
            self.name, self.annotation, self.value
        )


AnyIP = r"(\d+)\.(\d+)\.(\d+)\.(\d+)"
AnyDigit = r"(\d+)"
AnyStr = r"(.+)"
AnyUrl = r"(http[s]?://.+)"
Argument_T = Union[str, Type[MessageElement]]


class CommandInterface(BaseModel):
    name: str
    separator: str = " "

    def separate(self, sep: str):
        self.separator = sep
        return self

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class Option(CommandInterface):
    type: str = "OPT"
    args: Dict[str, Argument_T]

    def __init__(self, name: str, **kwargs):
        if name == "":
            raise ValueError("You can't give this with a null name !")
        super().__init__(
            name=name, args={k: v for k, v in kwargs.items() if k != "name"}
        )


class Subcommand(CommandInterface):
    type: str = "SBC"
    Options: List[Option]

    def __init__(self, name: str, *options: Option):
        if name == "":
            raise ValueError("You can't give this with a null name !")
        super().__init__(name=name, Options=list(options))


Options_T = List[Union[Subcommand, Option]]


class Arpamar(BaseModel):
    """
    亚帕玛尔(Arpamar), Alconna的珍藏宝书
    Example:
        1.`Arpamar.main_argument` :当Alconna写入了main_argument时,该参数返回对应的解析出来的值
        2.`Arpamar.header` :当Alconna的command内写有正则表达式时,该参数返回对应的匹配值
        3.`Arpamar.has` :判断Arpamar内是否有对应的属性
        4.`Arpamar.get` :返回Arpamar中指定的属性
        5.`Arpamar.matched` :返回命令是否匹配成功
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_index = 0  # 记录解析时当前字符串的index
        self.is_str = False  # 是否解析的是string
        self.results = {"options": {}}
        self.elements = {}
        self.raw_texts = []
        self.matched = False
        self.match_table = []
        self.need_marg = False

    @property
    def main_argument(self):
        if "main_argument" in self.results and self.need_marg:
            return self.results["main_argument"]

    @property
    def header(self):
        if "header" in self.results:
            return self.results["header"]

    def analysis_result(self) -> None:
        for k, v in self.results["options"].items():
            k = re.sub(r"`~\?/\.,<>;':\"\|\\!@#\$%\^&*\(\)_+-=}{\[]", "", k)
            self.__setattr__(k, v)

    def get(self, name: str) -> dict:
        return self.__getattribute__(name)

    def get_option_first_value(self, name: str) -> str:
        for i in self.results["options"][name].values():
            return i

    def get_option_values(self, name: str) -> List:
        t = []
        for i in self.results["options"][name].values():
            t.append(i)

    def has(self, name: str) -> bool:
        return name in self.__dict__

    def split_by(self, separate: str):
        _text = ""  # 重置
        _rest_text = ""

        if self.raw_texts[self.current_index][0]:  # 如果命令头匹配后还有字符串没匹配到
            _text, _rest_text = Alconna.split_once(
                self.raw_texts[self.current_index][0], separate
            )

        elif (
            not self.is_str and len(self.raw_texts) > 1
        ):  # 如果命令头匹配后字符串为空则有两种可能，这里选择不止一段字符串
            self.current_index += 1
            _text, _rest_text = Alconna.split_once(
                self.raw_texts[self.current_index][0], separate
            )

        return _text, _rest_text

    class Config:
        extra = "allow"


class Alconna(CommandInterface):
    """
    亚尔康娜（Alconna），Cesloi的妹妹
    用于更加奇怪(大雾)精确的命令解析，支持String与MessageChain
    样例：Alconna(
        headers=[""],
        command="name",
        options=[
            Subcommand("sub_name",Option("sub-opt", sub_arg=sub_arg)),
            Option("opt", arg=arg)
            ]
        main_argument=main_argument
        )
    其中
        - name: 命令名称
        - sub_name: 子命令名称
        - sub-opt: 子命令选项名称
        - sub_arg: 子命令选项参数
        - opt: 命令选项名称
        - arg: 命令选项参数
    Args:
        headers: 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与command至少有一个填写
        command: 命令名称，你的命令的名字，与headers至少有一个填写
        options: 命令选项，你的命令可选择的所有option,包括子命令与单独的选项
        main_argument: 主参数，填入后当且仅当命令中含有该参数时才会成功解析
    """

    name = "Alconna"
    headers: List[str]
    command: str
    options: Options_T
    main_argument: Argument_T

    def __init__(
        self,
        headers: Optional[List[str]] = None,
        command: Optional[str] = None,
        separator: Optional[str] = None,
        options: Optional[Options_T] = None,
        main_argument: Optional[Argument_T] = None,
    ):
        # headers与command二者必须有其一
        if all([all([not headers, not command]), not options, not main_argument]):
            raise ValueError("You must input one parameter!")
        super().__init__(
            headers=headers or [""],
            command=command or "",
            separator=separator or " ",
            options=options or [],
            main_argument=main_argument or "",
        )
        self._params = [self.main_argument]  # params是除开命令头的剩下部分
        self._params.extend(self.dict()["options"])

    @staticmethod
    def split_once(text: str, separate: str):  # 相当于另类的pop
        out_text = ""
        quotation_stack = []
        is_split = True
        for char in text:
            if char in "'\"":  # 遇到引号括起来的部分跳过分隔
                if not quotation_stack:
                    is_split = False
                    quotation_stack.append(char)
                else:
                    is_split = True
                    quotation_stack.pop(-1)
            if separate == char and is_split:
                break
            out_text += char
        return out_text, text.replace(out_text, "", 1).replace(separate, "", 1)

    @staticmethod
    def split(text: str, separate: str = " ", max_split: int = -1):
        text_list = []
        quotation_stack = []
        is_split = True
        while all([text, max_split]):
            out_text = ""
            for char in text:
                if char in "'\"":  # 遇到引号括起来的部分跳过分隔
                    if not quotation_stack:
                        is_split = False
                        quotation_stack.append(char)
                    else:
                        is_split = True
                        quotation_stack.pop(-1)
                if separate == char and is_split:
                    break
                out_text += char
            text_list.append(out_text)
            text = text.replace(out_text, "", 1).replace(separate, "", 1)
            max_split -= 1
        if text:
            text_list.append(text)
        return text_list

    def analysis_message(self, message: Union[str, MessageChain]) -> Arpamar:
        self.result = Arpamar()
        if isinstance(message, str):
            self.result.raw_texts.append([message, 0])
        else:
            message = message.copy().asSendable()
            for i, ele in enumerate(message):
                if ele.__class__.__name__ != "Plain":
                    self.result.elements[i] = ele
                else:
                    self.result.raw_texts.append([ele.text, i])

        _command_headers = []  # 依据headers与command生成一个列表，其中含有所有的命令头
        if self.headers != [""]:
            for i in self.headers:
                _command_headers.append(i + self.command)
        elif self.command != "":
            _command_headers.append(self.command)

        if self.main_argument != "":
            self.result.need_marg = True  # 如果need_marg那么match的元素里一定得有main_argument

        _head = False  # 先匹配命令头
        if self.result.raw_texts:
            _text, self.result.raw_texts[0][0] = self.result.split_by(self.separator)
            for ch in _command_headers:
                _head_find = re.findall("^" + ch + "$", _text)
                if _head_find:
                    _head = True
                    self.result.results["header"] = _head_find[0]
                    if (
                        self.result.results["header"] == _text
                    ):  # 如果命令头内没有正则表达式的话findall此时相当于fullmatch
                        del self.result.results["header"]
                    break

            _text_static = {}  # 统计字符串被切出来的次数
            while _head and not all([t[0] == "" for t in self.result.raw_texts]):
                try:
                    _text, _rest_text = self.result.split_by(self.separator)
                    for param in self._params:
                        try:  # 因为sub与opt一定是dict的，所以str型的param只能是marg
                            if isinstance(param, str):
                                _param_find = re.findall("^" + param + "$", _text)
                                if _param_find:
                                    self.result.results["main_argument"] = _param_find[
                                        0
                                    ]
                                    self.result.raw_texts[self.result.current_index][
                                        0
                                    ] = _rest_text
                            elif isinstance(param, dict):
                                if param["type"] == "OPT" and self._analysis_option(
                                    param,
                                    _text,
                                    _rest_text,
                                    self.result.results["options"],
                                ):
                                    del _text_static[_text]
                                elif param[
                                    "type"
                                ] == "SBC" and self._analysis_subcommand(
                                    param, _text, _rest_text
                                ):
                                    del _text_static[_text]
                            else:
                                # 既不是str也不是dict的情况下，认为param传入了一个类的Type
                                may_element_index = (
                                    self.result.raw_texts[self.result.current_index][1]
                                    + 1
                                )
                                if (
                                    type(self.result.elements[may_element_index])
                                    is param
                                ):
                                    self.result.results[
                                        "main_argument"
                                    ] = self.result.elements[may_element_index]
                                    del self.result.elements[may_element_index]
                        except KeyError:
                            pass
                        finally:
                            if _text not in _text_static:
                                _text_static[_text] = 1
                            else:
                                _text_static[_text] += 1
                            if _text_static[_text] > len(
                                self._params
                            ):  # 如果大于这个次数说明该text没有被任何参数匹配成功
                                _text_static[""] += 1
                except (IndexError, KeyError):
                    break
        else:
            _head = True
        try:
            # 如果没写options并且marg不是str的话，匹配完命令头后是进不去上面的代码的，这里单独拿一段出来
            may_element_index = self.result.raw_texts[self.result.current_index][1] + 1
            if (
                self.result.elements
                and type(self.result.elements[may_element_index]) is self._params[0]
            ):
                self.result.results["main_argument"] = self.result.elements[
                    may_element_index
                ]
                del self.result.elements[may_element_index]
        except (IndexError, KeyError):
            pass

        if (
            _head
            and len(self.result.elements) == 0
            and all([t[0] == "" for t in self.result.raw_texts])
            and (
                not self.result.need_marg
                or (self.result.need_marg and "main_argument" in self.result.results)
            )
        ):
            self.result.matched = True
            self.result.analysis_result()
        else:
            self.result.results.clear()
        return self.result

    def _analysis_option(self, param, text, rest_text, option_dict):
        opt = param["name"]
        arg = param["args"]
        sep = param["separator"]
        name, may_arg = self.split_once(text, sep)
        if sep == self.separator:  # 在sep等于separator的情况下name是被提前切出来的
            name = text
        if not re.match("^" + opt + "$", name):  # 先匹配选项名称
            return False
        self.result.raw_texts[self.result.current_index][0] = rest_text
        if arg == {}:
            option_dict[text] = text
            return True
        for k, v in arg.items():
            if isinstance(v, str):
                if sep == self.separator:
                    may_arg, rest_text = self.result.split_by(sep)
                if not re.match("^" + v + "$", may_arg):
                    return False
                if name not in option_dict:
                    option_dict[name] = {k: may_arg}
                else:
                    option_dict[name][k] = may_arg
                if sep == self.separator:
                    self.result.raw_texts[self.result.current_index][0] = rest_text
                return True
            else:
                may_element_index = (
                    self.result.raw_texts[self.result.current_index][1] + 1
                )
                if type(self.result.elements[may_element_index]) is not v:
                    return False
                if name not in option_dict:
                    option_dict[name] = {k: self.result.elements[may_element_index]}
                option_dict[name][k] = self.result.elements[may_element_index]
                del self.result.elements[may_element_index]
                return True

    def _analysis_subcommand(self, param, text, rest_text):
        subcommand = {}
        command = param["name"]
        sep = param["separator"]
        name, may_text = self.split_once(text, sep)
        if sep == self.separator:
            name = text
        if not re.match("^" + command + "$", name):
            return False
        self.result.raw_texts[self.result.current_index][0] = rest_text
        for option in param["Options"]:
            try:
                if sep == self.separator:
                    may_text, rest_text = self.result.split_by(sep)
                self._analysis_option(option, may_text, rest_text, subcommand)
            except (IndexError, KeyError):
                continue
        if name not in self.result.results["options"]:
            self.result.results["options"][name] = subcommand
        return True

    class Config:
        extra = "allow"


class AlconnaParser(BaseDispatcher):
    """
    Alconna的调度器形式
    """

    def __init__(self, *, alconna: Alconna):
        super().__init__()
        self.alconna = alconna

    def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        local_storage = interface.broadcast.decorator_interface.local_storage
        chain: MessageChain = interface.event.messageChain
        try:
            result = self.alconna.analysis_message(chain)
            if not result.results:
                raise ExecutionStop()
            local_storage["arpamar"] = result
        except:
            raise ExecutionStop()

    async def catch(self, interface: DispatcherInterface[MessageEvent]) -> Arpamar:
        local_storage = interface.broadcast.decorator_interface.local_storage
        arpamar = local_storage["arpamar"]
        if issubclass(interface.annotation, Arpamar):
            return arpamar
        if issubclass(interface.annotation, AlconnaParser):
            return self

    def afterExecution(
        self,
        interface: "DispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        if "arpamar" in interface.broadcast.decorator_interface.local_storage:
            del interface.broadcast.decorator_interface.local_storage["arpamar"]
