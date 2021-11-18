import asyncio
import functools
import importlib
from asyncio.events import AbstractEventLoop
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Awaitable, Callable, ClassVar, Dict, Tuple, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")

R = TypeVar("R")


class ParallelExecutor:
    """并行执行器.

    推荐使用 Ariadne.create 以自动绑定事件循环.
    """

    thread_exec: ThreadPoolExecutor
    proc_exec: ProcessPoolExecutor
    loop_ref_dict: ClassVar[Dict[AbstractEventLoop, "ParallelExecutor"]] = {}
    func_mapping: ClassVar[Dict[str, Callable[P, R]]] = {}

    def __init__(
        self,
        loop: AbstractEventLoop = None,
        max_thread: int = None,
        max_process: int = None,
    ):
        """初始化并行执行器.

        Args:
            loop (AbstractEventLoop, optional): 要绑定的事件循环. Defaults to None.
            max_thread (int, optional): 最大线程数. Defaults to None.
            max_process (int, optional): 最大进程数. Defaults to None.

        `max_thread` 与 `max_process` 参数默认值请参阅 `concurrent.futures`.
        """
        self.thread_exec = ThreadPoolExecutor(max_workers=max_thread)
        self.proc_exec = ProcessPoolExecutor(max_workers=max_process)
        if loop:
            self.bind_loop(loop)

    @classmethod
    def get(cls, loop: AbstractEventLoop):
        if loop not in cls.loop_ref_dict:
            cls.loop_ref_dict[loop] = ParallelExecutor()
        return cls.loop_ref_dict[loop]

    def bind_loop(self, loop: AbstractEventLoop):
        self.loop_ref_dict[loop] = self

    @classmethod
    def shutdown(cls):
        for exec in cls.loop_ref_dict.values():
            exec.thread_exec.shutdown()
            exec.proc_exec.shutdown()

    @classmethod
    def run_func(cls, name: str, module: str, args: tuple, kwargs: dict) -> R:
        importlib.import_module(module)
        return cls.func_mapping[name](*args, **kwargs)


def io_bound(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    ParallelExecutor.func_mapping[func.__qualname__] = func

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
    ParallelExecutor.func_mapping[func.__qualname__] = func

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        loop = asyncio.get_running_loop()
        executor = ParallelExecutor.get(loop)
        return await loop.run_in_executor(
            executor.proc_exec,
            ParallelExecutor.run_func,
            func.__qualname__,
            func.__module__,
            args,
            kwargs,
        )

    return wrapper
