import os
import inspect
import pathlib
import typing


# PATH HELPERS


def resolve_path(
    path: pathlib.Path, relative: pathlib.Path | None = None
) -> pathlib.Path:
    """
    Given a path, resolves it to a real path. Optionally, specify that the path
    is given relative to some other path. For instance, if path is "../file.py" and
    relative is "a/b/c/reference.py", then this function computes "/a/b/c/../file.py"
    and deferences the symbolic links to yield "/a/b/file.py".
    """
    if relative is not None:
        return pathlib.Path(
            os.path.realpath(os.path.join(os.path.dirname(relative), path))
        )
    else:
        return pathlib.Path(os.path.realpath(path))


# REFLECTIVE HELPERS


def call_prepared(func: typing.Callable, kwargs: dict):
    """
    Calls a function with unrolled keyword arguments.
    """
    return func(**prepare_kwargs(func, kwargs))


def prepare_kwargs(func: typing.Callable, kwargs: dict) -> dict:
    """
    Filters a dictionary of arguments into one that only provides the keyword
    arguments present in the signature of the given function.
    """
    if not kwargs:
        return {}

    return {k: v for k, v in kwargs.items() if k in unroll_params(func)}


def unroll_params(func: typing.Callable) -> list[str]:
    """
    Returns a list of parameter names in the given function.
    """
    return [param.name for param in inspect.signature(func).parameters.values()]


# WRAPPERS


def did_except(func, *args, **kwargs) -> bool:
    """
    Determines if the execution of a sync funtion raised an exception.
    """
    try:
        func(*args, **kwargs)
        return False
    except Exception:
        return True
