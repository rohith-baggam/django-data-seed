import threading
from typing import Any, Optional

_thread_locals = threading.local()


def set_thread_variable(name: str, value: Any) -> None:
    """
    Sets a thread-local variable.

    Args:
        name (str): The name of the thread-local variable to set.
        value (Any): The value to assign to the thread-local variable.

    Returns:
        None
    """
    setattr(_thread_locals, name, value)


def get_thread_variable(name: str, default: Optional[Any] = None) -> Any:
    """
    Retrieves the value of a thread-local variable.

    Args:
        name (str): The name of the thread-local variable to retrieve.
        default (Optional[Any]): The default value to return if the variable is not found.

    Returns:
        Any: The value of the thread-local variable, or the default value if not found.
    """
    return getattr(_thread_locals, name, default)


def clear_thread_variable(name: str) -> None:
    """
    Clears a thread-local variable.

    Args:
        name (str): The name of the thread-local variable to clear.

    Returns:
        None
    """
    if hasattr(_thread_locals, name):
        delattr(_thread_locals, name)
