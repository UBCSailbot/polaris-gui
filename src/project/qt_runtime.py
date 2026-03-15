from __future__ import annotations

import ctypes
import importlib.util
import sys
from pathlib import Path


_BUNDLED_QT_LIBRARIES = (
    "libQt5Core.so.5",
    "libQt5DBus.so.5",
    "libQt5Network.so.5",
    "libQt5Gui.so.5",
    "libQt5Widgets.so.5",
    "libQt5XcbQpa.so.5",
)


def configure_bundled_qt_runtime() -> None:
    """Preload PyQt's bundled Qt libs so platform plugins don't bind to system Qt."""
    if not sys.platform.startswith("linux"):
        return

    spec = importlib.util.find_spec("PyQt5")
    if spec is None or not spec.submodule_search_locations:
        return

    qt_lib_dir = Path(next(iter(spec.submodule_search_locations))) / "Qt5" / "lib"
    if not qt_lib_dir.is_dir():
        return

    for library_name in _BUNDLED_QT_LIBRARIES:
        library_path = qt_lib_dir / library_name
        if not library_path.is_file():
            continue
        try:
            ctypes.CDLL(str(library_path), mode=ctypes.RTLD_GLOBAL)
        except OSError:
            # Fall back to the system loader if this environment doesn't ship bundled Qt libs.
            continue
