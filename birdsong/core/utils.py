import os
import inspect
import logging
import pathlib
import sys
import typing


# LOGGING


class StreamFormatter(logging.Formatter):
    """
    A clean formatter for birdsong's logger.
    """

    LEVEL_COLOURS = [
        (logging.DEBUG, "\x1b[38;5;183m"),
        (logging.INFO, "\x1b[38;5;45m"),
        (logging.WARNING, "\x1b[38;5;221m"),
        (logging.ERROR, "\x1b[38;5;203m"),
        (logging.CRITICAL, "\x1b[38;5;160m"),
    ]

    FORMATS = {
        level: logging.Formatter(
            f"\x1b[38;5;8m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[38;5;15m%(name)s\x1b[0m %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f"\x1b[38;5;160m{text}\x1b[0m"

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def stream_supports_colour(stream: any) -> bool:
    """
    Courtesy of discord.py. Checks if a stream is a colour stream.
    """
    is_a_tty = hasattr(stream, "isatty") and stream.isatty()

    if "PYCHARM_HOSTED" in os.environ:
        return is_a_tty

    if os.environ.get("TERM_PROGRAM") == "vscode":
        return is_a_tty

    if sys.platform != "win32":
        return is_a_tty

    return is_a_tty and ("ANSICON" in os.environ or "WT_SESSION" in os.environ)


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
