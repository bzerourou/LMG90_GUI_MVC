# rthook_qt6.py
import os
import sys

# ── Un seul runtime de threads (MKL / OpenMP) ───────────────────────────────
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL"   # pas de libiomp parallèle
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

def _setup_dll_paths():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    os.environ["PATH"] = base + os.pathsep + os.environ.get("PATH", "")
    for d in (
        base,
        os.path.join(base, "pylmgc90"),
        os.path.join(base, "pylmgc90", "chipy"),
        os.path.join(base, "numpy.libs"),
        os.path.join(base, "numpy", ".libs"),
    ):
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except (OSError, AttributeError):
                pass

_setup_dll_paths()


def _fix_qt6_plugins():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base, "PyQt6", "Qt6", "plugins"),
        os.path.join(base, "PyQt6", "Qt6", "plugins", "platforms"),
        os.path.join(base, "plugins"),
        os.path.join(base, "platforms"),
        base,
    ]
    platforms_dir = None
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "qwindows.dll")):
            platforms_dir = candidate
            break
        if os.path.isdir(candidate):
            for root, dirs, files in os.walk(candidate):
                if "qwindows.dll" in files:
                    platforms_dir = root
                    break
        if platforms_dir:
            break
    if platforms_dir:
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms_dir
        os.environ["QT_PLUGIN_PATH"] = os.path.dirname(platforms_dir)

_fix_qt6_plugins()