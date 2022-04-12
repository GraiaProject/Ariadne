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
        data (dict): 返回的对象

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
