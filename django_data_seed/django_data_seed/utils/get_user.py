import threading
from typing import Any
_thread_locals = threading.local()


def get_current_user() -> Any:
    """
    Retrieves the current user from thread-local storage.

    Returns:
        Any: The user object from thread-local storage, or None if no user is set.

    Description:
        This function fetches the user object that is stored in the thread-local storage.
        It is typically used to access the currently logged-in user in a thread-safe manner.
    """
    return getattr(_thread_locals, 'user', None)


def set_current_user(user: Any) -> None:
    """
    Sets the current user in thread-local storage.

    Args:
        user (Any): The user object to be stored in thread-local storage.

    Description:
        This function stores the provided user object in thread-local storage.
        It is used to make the current user accessible across different parts of the application
        within the same thread.
    """
    _thread_locals.user = user
