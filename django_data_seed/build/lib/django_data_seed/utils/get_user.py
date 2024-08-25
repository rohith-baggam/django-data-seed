from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
import threading
from typing import Any
_thread_locals = threading.local()


User = get_user_model()  # Get the user model class


def get_current_user() -> Any:
    """
    Retrieves the current user from thread-local storage.

    Returns:
        Any: The user object from thread-local storage, or None if the user is anonymous or not set.

    Description:
        This function fetches the user object that is stored in thread-local storage.
        It is typically used to access the currently logged-in user in a thread-safe manner.
    """
    user = getattr(_thread_locals, 'user', None)

    if isinstance(user, User) and not isinstance(user, AnonymousUser):
        return user
    return None


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
