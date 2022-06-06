"""本模块提供并行执行器, 及方便函数 `io_bound`, `cpu_bound`.

提示: 若需要代替, 建议使用 `unsync` 库.
"""
import asyncio
import functools
import importlib
import multiprocessing
from asyncio.events import AbstractEventLoop
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Awaitable, Callable, ClassVar, Dict, Optional, Tuple

from ..typing import P, R


def IS_MAIN_PROCESS() -> bool:
    """返回是否为主进程

    Returns:
        bool: 是否为主进程
    """
    return multiprocessing.parent_process() is None


def _reg_sigint():
    """在子进程注册 SIGINT 处理函数以防止 Traceback 炸屏"""
    import signal
    import sys

    signal.signal(signal.SIGINT, lambda *_, **__: sys.exit())


class ParallelExecutor:
    """并行执行器."""

    thread_exec: ThreadPoolExecutor
    proc_exec: ProcessPoolExecutor
    loop_ref_dict: ClassVar[Dict[AbstractEventLoop, "ParallelExecutor"]] = {}
    func_mapping: ClassVar[Dict[Tuple[str, str], Callable]] = {}

    def __init__(
        self,
        loop: Optional[AbstractEventLoop] = None,
        max_thread: Optional[int] = None,
        max_process: Optional[int] = None,
    ):
        """初始化并行执行器.

        Args:
            loop (AbstractEventLoop, optional): 要绑定的事件循环, 会自动获取当前事件循环. Defaults to None.
            max_thread (int, optional): 最大线程数. Defaults to None.
            max_process (int, optional): 最大进程数. Defaults to None.

        `max_thread` 与 `max_process` 参数默认值请参阅 `concurrent.futures`.
        """
        self.thread_exec = ThreadPoolExecutor(max_workers=max_thread)
        self.proc_exec = ProcessPoolExecutor(
            max_workers=max_process, initializer=_reg_sigint
        )  # see issue #50
        self.bind_loop(loop or asyncio.get_running_loop())

    @classmethod
    def get(cls, loop: Optional[AbstractEventLoop] = None) -> "ParallelExecutor":
        """获取 ParallelExecutor 实例

        Args:
            loop (AbstractEventLoop, optional): 查找的事件循环. Defaults to None.

        Returns:
            ParallelExecutor: 找到的 / 新创建的 ParallelExecutor.
        """
        loop = loop or asyncio.get_running_loop()
        if loop not in cls.loop_ref_dict:
            cls.loop_ref_dict[loop] = ParallelExecutor()
        return cls.loop_ref_dict[loop]

    def bind_loop(self, loop: AbstractEventLoop):
        """绑定本实例到 loop.

        Args:
            loop (AbstractEventLoop): 要绑定到的事件循环.
        """
        self.loop_ref_dict[loop] = self

    @classmethod
    def shutdown(cls):
        """关闭本类的所有底层 Executor."""
        for exec in cls.loop_ref_dict.values():
            exec.close()

    def close(self):
        """关闭实例的所有底层 Executor."""
        self.thread_exec.shutdown()
        self.proc_exec.shutdown()

    @classmethod
    def run_func(cls, name: str, module: str, args: tuple, kwargs: dict) -> Any:
        """运行函数的实现

        Args:
            name (str): 函数名 (__qualname__)
            module (str): 函数所在模块名 (__module__)
            args (tuple): 位置参数
            kwargs (dict): 关键字参数

        Returns:
            Any: 底层函数的返回值
        """
        importlib.import_module(module)
        return cls.func_mapping[module, name](*args, **kwargs)

    @classmethod
    def run_func_static(cls, func: Callable[..., R], args: tuple, kwargs: dict) -> R:
        """调用一个静态函数 (会自动解包装已被 ParallelExecutor 包装过的函数)

        Args:
            func (Callable[..., R]): 要调用的函数
            args (tuple): 位置参数
            kwargs (dict): 关键字参数

        Returns:
            R: 底层函数的返回值
        """
        if (func.__module__, func.__qualname__) in cls.func_mapping:
            func = cls.func_mapping[func.__module__, func.__qualname__]
        return func(*args, **kwargs)  # type: ignore

    def to_thread(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        """在线程中异步运行 func 函数.

        Args:
            func (Callable[P, R]): 要调用的函数.
            *args (P.args): 附带的位置参数.
            **kwargs (P.kwargs): 附带的关键词参数.

        Returns:
            Future[R]: 返回结果. 需要被异步等待.
        """
        return asyncio.get_running_loop().run_in_executor(  # type: ignore
            self.thread_exec,
            ParallelExecutor.run_func_static,
            func,
            args,
            kwargs,
        )

    def to_process(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        """在进程中异步运行 func 函数. 需要先注册过才行.

        Args:
            func (Callable[P, R]): 要调用的函数.
            *args (P.args): 附带的位置参数.
            **kwargs (P.kwargs): 附带的关键词参数.

        Returns:
            Future[R]: 返回结果. 需要被异步等待.
        """
        return asyncio.get_running_loop().run_in_executor(  # type: ignore
            self.proc_exec,
            ParallelExecutor.run_func_static,
            func,
            args,
            kwargs,
        )


def io_bound(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """包装一个函数在线程中异步运行.

    Args:
        func (Callable[P, R]): 要包装的函数

    Returns:
        Callable[P, Awaitable[R]]: 包装后的函数
    """
    ParallelExecutor.func_mapping[func.__module__, func.__qualname__] = func

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        loop = asyncio.get_running_loop()
        executor = ParallelExecutor.get(loop)
        return await loop.run_in_executor(
            executor.thread_exec,
            ParallelExecutor.run_func,
            func.__qualname__,
            func.__module__,
            args,
            kwargs,
        )

    return wrapper


def cpu_bound(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """包装一个函数在进程中异步运行.

    Args:
        func (Callable[P, R]): 要包装的函数

    Returns:
        Callable[P, Awaitable[R]]: 包装后的函数
    """
    mod = func.__module__
    ParallelExecutor.func_mapping["__main__" if mod == "__mp_main__" else mod, func.__qualname__] = func

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        mod = func.__module__
        loop = asyncio.get_running_loop()
        executor = ParallelExecutor.get(loop)
        return await loop.run_in_executor(
            executor.proc_exec,
            ParallelExecutor.run_func,
            func.__qualname__,
            "__main__" if mod == "__mp_main__" else mod,
            args,
            kwargs,
        )

    return wrapper
