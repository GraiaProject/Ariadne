class ParamsUnmatched(Exception):
    """一个 text 没有被任何参数匹配成功"""


class InvalidOptionName(Exception):
    """option或subcommand的名字中填入了非法的字符"""


class NullName(Exception):
    """命令的名称写入了空字符"""
