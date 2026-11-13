"""Helper methods to inspect exception traces."""

from inspect import FrameInfo


def search_stack_locals[T](cls: type[T], stack: list[FrameInfo]) -> T | None:
    """Search the local variables on the given stack for the first instance of `T`."""

    for element in stack:
        for value in element.frame.f_locals.values():
            if isinstance(value, cls):
                return value

    return None
