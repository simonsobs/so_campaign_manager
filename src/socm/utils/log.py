"""Logging for socm components, based on loguru.

Each component (bookkeeper, planner, enactor) gets a logger bound to its uid
and its own log file, ``<path>/<uid>.log``, in the session directory. What is
shown on the console is configured once by the CLI with
:func:`configure_console`; the library itself never removes loguru handlers.
"""

import os
import sys
import threading

from loguru import logger

# Environment variable selecting the console log level for the socm CLI.
CONSOLE_LEVEL_ENV = "SOCM_LOG_LEVEL"

_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {extra[uid]:<16} | {thread.name:<12} | {level:<8} | {message}"

_sinks: dict[str, int] = {}
_sinks_lock = threading.Lock()
_console_sink: int | None = None


def get_logger(uid: str, path: str, level: str = "DEBUG"):
    """
    Return a logger for one component, writing to ``<path>/<uid>.log``.

    Calling it again with the same file returns a logger for the same sink
    instead of adding another one.

    Parameters
    ----------
    uid : str
        Component identifier, e.g. ``"enactor.0000"``; also the log file name.
    path : str
        Directory of the log file (the session directory).
    level : str, optional
        Minimum level written to the file. Defaults to ``"DEBUG"``.

    Returns
    -------
    loguru.Logger
        A logger bound to ``uid``. Use ``{}`` placeholders for arguments,
        e.g. ``log.info("Workflow {} done", wf_id)``.
    """
    log_file = os.path.join(path, f"{uid}.log")
    with _sinks_lock:
        if log_file not in _sinks:
            _sinks[log_file] = logger.add(
                log_file,
                level=level,
                format=_FILE_FORMAT,
                filter=lambda record: record["extra"].get("log_file") == log_file,
            )
    return logger.bind(uid=uid, log_file=log_file)


def configure_console(level: str | None = None) -> None:
    """
    Replace loguru's default console handler with one at ``level``.

    Meant for the CLI entry point only. The level defaults to
    ``$SOCM_LOG_LEVEL`` or ``WARNING``, so the per-component DEBUG messages
    go to the session log files but not to the terminal.
    """
    global _console_sink
    level = level or os.environ.get(CONSOLE_LEVEL_ENV, "WARNING")
    # loguru's default stderr handler has id 0; ours replaces it (and itself on re-configuration).
    for sink_id in (0, _console_sink):
        if sink_id is not None:
            try:
                logger.remove(sink_id)
            except ValueError:
                pass  # already removed
    _console_sink = logger.add(sys.stderr, level=level)
