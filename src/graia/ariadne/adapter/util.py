from asyncio import Future
from typing import Any, Dict, Type, Union

from ..exception import (
    AccountMuted,
    AccountNotFound,
    InvalidArgument,
    InvalidSession,
    InvalidVerifyKey,
    MessageTooLong,
    RemoteException,
    UnknownError,
    UnknownTarget,
    UnVerifiedSession,
)


class SyncIDManager:
    def __init__(self) -> None:
        self.id_map: Dict[int, Future] = {0: ...}

    def allocate(self, fut: Future) -> int:
        """分配一个新的 Sync ID, 并将其与指定的 Future 关联.

        Returns:
            int: 生成的 Sync ID. 注意完成后使用 free() 方法标记本 Sync ID.
        """
        new_id = max(self.id_map) + 1
        self.id_map[new_id] = fut
        return new_id

    def free(self, sync_id: int, result: Any) -> bool:
        """标记一个 Sync ID 的任务完成. 本 Sync ID 随后可被复用.

        Args:
            sync_id (int): 标记的 Sync ID.
            result (Any): 任务结果
        Returns:
            bool: 是否成功标记.
        """
        if sync_id in self.id_map:
            fut = self.id_map.pop(sync_id)
            if isinstance(result, Exception):
                fut.set_exception(result)
            else:
                fut.set_result(result)
            return True
        return False


code_exceptions_mapping: Dict[int, Type[Exception]] = {
    1: InvalidVerifyKey,
    2: AccountNotFound,
    3: InvalidSession,
    4: UnVerifiedSession,
    5: UnknownTarget,
    6: FileNotFoundError,
    10: PermissionError,
    20: AccountMuted,
    30: MessageTooLong,
    400: InvalidArgument,
    500: RemoteException,
}


def validate_response(data: Dict[str, Any]) -> Union[dict, Exception]:
    """验证远程服务器的返回值

    Args:
        code (dict): 返回的对象

    Raises:
        Exception: 请参照 code_exceptions_mapping
    """
    if isinstance(data, dict):
        int_code: int = data.get("code")
    else:
        int_code = data
    if not isinstance(int_code, int) or int_code == 200 or int_code == 0:
        if "data" in data:
            return data["data"]
        return data
    exc_cls = code_exceptions_mapping.get(int_code)
    if exc_cls:
        return exc_cls(exc_cls.__doc__, data)
    return UnknownError(data)
