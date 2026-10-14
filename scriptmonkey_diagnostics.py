# -*- coding: utf-8 -*-
"""Crash-aware diagnostics for ScriptMonkey.

ide.log is the ordinary application log. crash.log is created only after an
uncaught Python exception. Native crashes are written to a temporary pending
file and promoted to crash.log on the next start if the process did not exit
cleanly.
"""
from __future__ import annotations

import atexit
import faulthandler
import logging
import os
import shutil
import sys
import threading
import traceback
import warnings
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".scriptmonkey_addons" / "logs"
_LOG_FILE = _LOG_DIR / "ide.log"
_CRASH_FILE = _LOG_DIR / "crash.log"
_PENDING_CRASH_FILE = _LOG_DIR / "crash.pending.log"
_LOGGER = logging.getLogger("scriptmonkey")
_LOGGING_READY = False
_FAULT_HANDLER_STREAM = None
_ORIGINAL_STDOUT = sys.stdout
_ORIGINAL_STDERR = sys.stderr


class _TeeStream:
    """Keep terminal output intact while copying it into the application log."""
    def __init__(self, original, level):
        self._original = original
        self._level = level
        self._partial = ""

    def write(self, value):
        if not isinstance(value, str):
            value = str(value)
        try:
            self._original.write(value)
        except Exception:
            pass
        self._partial += value
        while "\n" in self._partial:
            line, self._partial = self._partial.split("\n", 1)
            if line.strip():
                _LOGGER.log(self._level, "[stream] %s", line)
        return len(value)

    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass
        if self._partial.strip():
            _LOGGER.log(self._level, "[stream] %s", self._partial)
            self._partial = ""

    def isatty(self):
        try:
            return self._original.isatty()
        except Exception:
            return False

    def fileno(self):
        return self._original.fileno()

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8")


def _write_crash(exc_type, exc_value, exc_tb, label):
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _CRASH_FILE.open("a", encoding="utf-8") as crash:
        crash.write("\n" + "=" * 90 + "\n")
        crash.write(f"Time: {datetime.now().astimezone().isoformat()}\n")
        crash.write(f"Type: {label}\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=crash)
        crash.flush()


def _promote_native_crash_if_present():
    # faulthandler cannot run Python cleanup during an access violation or
    # native abort. A leftover pending file therefore indicates an unclean exit.
    try:
        if _PENDING_CRASH_FILE.exists() and _PENDING_CRASH_FILE.stat().st_size:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            with _CRASH_FILE.open("a", encoding="utf-8") as dest, _PENDING_CRASH_FILE.open("r", encoding="utf-8", errors="replace") as source:
                dest.write("\n" + "=" * 90 + "\nNative crash details from previous run:\n")
                shutil.copyfileobj(source, dest)
            _PENDING_CRASH_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _cleanup_pending_file():
    try:
        if _FAULT_HANDLER_STREAM is not None:
            _FAULT_HANDLER_STREAM.flush()
            _FAULT_HANDLER_STREAM.close()
        # A normal process exit leaves only the faulthandler header. Remove it.
        if _PENDING_CRASH_FILE.exists():
            _PENDING_CRASH_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def install_logging():
    global _LOGGING_READY, _FAULT_HANDLER_STREAM
    if _LOGGING_READY:
        return
    _LOGGING_READY = True
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        _promote_native_crash_if_present()
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        if not any(getattr(h, "_scriptmonkey_file_handler", False) for h in root.handlers):
            handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)
            handler._scriptmonkey_file_handler = True
            root.addHandler(handler)
        if not any(getattr(h, "_scriptmonkey_console_handler", False) for h in root.handlers):
            handler = logging.StreamHandler(_ORIGINAL_STDERR)
            handler.setLevel(logging.INFO)
            handler.setFormatter(formatter)
            handler._scriptmonkey_console_handler = True
            root.addHandler(handler)
        logging.captureWarnings(True)
        warnings.simplefilter("default")
        sys.stdout = _TeeStream(_ORIGINAL_STDOUT, logging.INFO)
        sys.stderr = _TeeStream(_ORIGINAL_STDERR, logging.ERROR)

        def main_exception(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            _LOGGER.critical("Uncaught main-thread exception", exc_info=(exc_type, exc_value, exc_tb))
            try:
                _write_crash(exc_type, exc_value, exc_tb, "uncaught Python exception (main thread)")
            except Exception:
                _LOGGER.exception("Could not write crash log")
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        sys.excepthook = main_exception

        if hasattr(threading, "excepthook"):
            def thread_exception(args):
                _LOGGER.critical("Uncaught thread exception in %s", getattr(args.thread, "name", "<unknown>"),
                                 exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
                try:
                    _write_crash(args.exc_type, args.exc_value, args.exc_traceback,
                                 f"uncaught thread exception; thread={args.thread!r}")
                except Exception:
                    _LOGGER.exception("Could not write thread crash log")
                threading.__excepthook__(args)
            threading.excepthook = thread_exception

        # The native-crash handler writes to a temporary file, never directly to crash.log.
        _FAULT_HANDLER_STREAM = _PENDING_CRASH_FILE.open("w", encoding="utf-8", buffering=1)
        _FAULT_HANDLER_STREAM.write(
            f"Diagnostic session: {datetime.now().astimezone().isoformat()}\n"
            f"Python: {sys.version}\nExecutable: {sys.executable}\nPlatform: {sys.platform}\n"
        )
        faulthandler.enable(file=_FAULT_HANDLER_STREAM, all_threads=True)
        atexit.register(_cleanup_pending_file)

        try:
            from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
            def qt_message_handler(mode, context, message):
                levels = {
                    QtMsgType.QtDebugMsg: logging.DEBUG,
                    QtMsgType.QtInfoMsg: logging.INFO,
                    QtMsgType.QtWarningMsg: logging.WARNING,
                    QtMsgType.QtCriticalMsg: logging.ERROR,
                    QtMsgType.QtFatalMsg: logging.CRITICAL,
                }
                where = f" ({context.file}:{context.line}, {context.function})" if context else ""
                _LOGGER.log(levels.get(mode, logging.INFO), "Qt%s: %s%s",
                            " fatal" if mode == QtMsgType.QtFatalMsg else "", message, where)
            qInstallMessageHandler(qt_message_handler)
        except Exception:
            _LOGGER.exception("Could not install Qt message handler")
        _LOGGER.info("ScriptMonkey logging initialized; app log: %s", _LOG_FILE)
        _LOGGER.info("Crash log will be created only after a crash: %s", _CRASH_FILE)
    except Exception:
        try:
            sys.__stderr__.write("Failed to initialize ScriptMonkey logging:\n" + traceback.format_exc())
        except Exception:
            pass


def _log_runtime_event(event, **details):
    try:
        _LOGGER.info("%s | %s", event, details if details else "")
    except Exception:
        pass
