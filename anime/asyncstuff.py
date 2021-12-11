# Future Imports
from __future__ import annotations

# Standard Library Imports
import asyncio
import functools


def asyncexe():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            partial = functools.partial(func, *args, **kwargs)
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(None, partial)

        return wrapper

    return decorator
