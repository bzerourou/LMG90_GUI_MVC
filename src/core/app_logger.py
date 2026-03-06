# ============================================================================
# app_logger.py  —  Système de log global de LMGC90_GUI
# ============================================================================
"""
Logger global pour toute l'application.

Usage depuis n'importe quel module :

    from ...core.app_logger import get_logger
    log = get_logger()
    log.info("message")
    log.warning("attention")
    log.error("erreur")

Le logger est initialisé une seule fois dans main.py avant tout import
pylmgc90. Il capture :
  - tous les appels log.*/logging.*
  - stdout et stderr Python (donc les print() et les warnings pylmgc90)
  - les exceptions non gérées (sys.excepthook)

Chaque session crée un nouveau fichier :
    <AppData>/LMGC90_GUI/logs/lmgc90_gui_YYYYMMDD_HHMMSS.log
"""

import logging
import sys
import os
import datetime
import warnings
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# ── Singleton ─────────────────────────────────────────────────────────────────
_logger: Optional[logging.Logger] = None
_log_path: Optional[Path]         = None
_log_dir:  Optional[Path]         = None


# ── Répertoire de logs ────────────────────────────────────────────────────────
def _default_log_dir() -> Path:
    """Retourne le répertoire de logs par défaut selon l'OS."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "LMGC90_GUI" / "logs"


# ── Format des messages ───────────────────────────────────────────────────────
_FMT_FILE    = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
_FMT_CONSOLE = "[%(levelname)-8s] %(message)s"
_DATE_FMT    = "%Y-%m-%d %H:%M:%S"


# ── Redirigeur stdout/stderr → logger ────────────────────────────────────────
class _StreamToLogger:
    """
    Redirige un flux texte (stdout/stderr) vers le logger.

    Fonctionne en mode dev (original = console) ET en mode prod PyInstaller
    (original peut etre None quand l'exe est construit sans console
    --noconsole / --windowed).
    """

    # Messages a ne pas stocker dans le log (bruit inutile)
    _IGNORE = (
        "pkg_resources is deprecated",
        "pkg_resources package is slated",
        "vtk display not available",
        "to activate it install python",
    )

    def __init__(self, logger: logging.Logger, level: int, original):
        self._logger   = logger
        self._level    = level
        # original peut etre None en prod frozen sans console
        self._original = original if original is not None else None
        self._buf      = ""

    def write(self, msg: str):
        if not msg:
            return
        # Ecrire sur la console originale seulement si elle existe
        if self._original is not None:
            try:
                self._original.write(msg)
                self._original.flush()
            except Exception:
                pass  # console fermee ou indisponible : on continue quand meme

        # Accumuler et envoyer au logger ligne par ligne
        self._buf += msg
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip()
            if line and not any(p in line for p in self._IGNORE):
                self._logger.log(self._level, line)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def fileno(self):
        # fileno() est requis par certains modules C (ex: Fortran via ctypes).
        # Si le flux original n'existe pas, on leve UnsupportedOperation
        # plutot qu'un AttributeError ou NoneType.
        if self._original is not None:
            try:
                return self._original.fileno()
            except Exception:
                pass
        import io
        raise io.UnsupportedOperation("fileno")

    def isatty(self):
        if self._original is not None:
            return getattr(self._original, 'isatty', lambda: False)()
        return False


# ── Gestionnaire d'exceptions non gérées ─────────────────────────────────────
def _handle_exception(exc_type, exc_value, exc_tb):
    """Capture les exceptions non gérées et les écrit dans le log."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger = get_logger()
    logger.critical(
        "Exception non gérée",
        exc_info=(exc_type, exc_value, exc_tb)
    )


# ── Gestionnaire de warnings Python ──────────────────────────────────────────
def _log_warning(message, category, filename, lineno, file=None, line=None):
    """Redirige les warnings Python vers le logger (sauf les indésirables)."""
    msg_str = str(message)
    # Ignorer les warnings pkg_resources / vtk
    if any(p in msg_str for p in (
        "pkg_resources is deprecated",
        "pkg_resources package is slated",
        "vtk display not available",
        "to activate it install python",
    )):
        return
    logger = get_logger()
    logger.warning(
        f"{category.__name__}: {msg_str}  [{filename}:{lineno}]"
    )


# ── Initialisation ────────────────────────────────────────────────────────────
def init_logger(log_dir: Optional[Path] = None, level: int = logging.DEBUG) -> logging.Logger:
    """
    Initialise le logger global. À appeler UNE SEULE FOIS dans main.py,
    avant tout import de pylmgc90 ou de Qt.

    Args:
        log_dir: Répertoire de logs. Par défaut : AppData/LMGC90_GUI/logs/
        level:   Niveau de logging. Par défaut DEBUG (tout capturer).

    Returns:
        Le logger configuré.
    """
    global _logger, _log_path, _log_dir

    if _logger is not None:
        return _logger  # déjà initialisé

    # ── Répertoire ────────────────────────────────────────────────────────────
    _log_dir = Path(log_dir) if log_dir else _default_log_dir()
    _log_dir.mkdir(parents=True, exist_ok=True)

    # Nom de fichier horodaté
    stamp     = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_path = _log_dir / f"lmgc90_gui_{stamp}.log"

    # ── Logger racine ─────────────────────────────────────────────────────────
    _logger = logging.getLogger("lmgc90_gui")
    _logger.setLevel(level)
    _logger.propagate = False  # ne pas propager au root logger

    # ── Handler fichier (rotation : 5 Mo × 3 fichiers) ────────────────────────
    fh = RotatingFileHandler(
        _log_path, maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_FMT_FILE, datefmt=_DATE_FMT))
    _logger.addHandler(fh)

    # ── Handler console (WARNING+ uniquement pour ne pas polluer) ─────────────
    # sys.__stdout__ peut etre None en prod frozen sans console (--windowed).
    # Dans ce cas on n'ajoute pas de handler console : les messages vont
    # uniquement dans le fichier log.
    _real_stdout = sys.__stdout__
    if _real_stdout is not None:
        ch = logging.StreamHandler(_real_stdout)
        ch.setLevel(logging.WARNING)
        ch.setFormatter(logging.Formatter(_FMT_CONSOLE))
        _logger.addHandler(ch)

    # ── En-tête du fichier log ────────────────────────────────────────────────
    _logger.info("=" * 70)
    _logger.info(f"LMGC90_GUI — session démarrée le {datetime.datetime.now().isoformat()}")
    _logger.info(f"Python {sys.version}")
    _logger.info(f"Plateforme : {sys.platform}")
    _logger.info(f"Exécutable : {sys.executable}")
    _logger.info(f"Frozen : {getattr(sys, 'frozen', False)}")
    _logger.info(f"Fichier log : {_log_path}")
    _logger.info("=" * 70)

    # ── Redirection stdout / stderr → logger ──────────────────────────────────
    # On capture les flux ACTUELS (avant tout remplacement PyInstaller).
    # sys.stdout / sys.stderr peuvent deja etre None en prod frozen
    # (--windowed) : _StreamToLogger gere ce cas proprement.
    sys.stdout = _StreamToLogger(_logger, logging.INFO,    sys.stdout)
    sys.stderr = _StreamToLogger(_logger, logging.WARNING, sys.stderr)

    # ── Hook exceptions non gérées ────────────────────────────────────────────
    sys.excepthook = _handle_exception

    # ── Hook warnings Python ──────────────────────────────────────────────────
    warnings.showwarning = _log_warning
    # Supprimer les warnings pkg_resources / vtk
    for pat in (
        ".*pkg_resources is deprecated.*",
        ".*pkg_resources package is slated.*",
        ".*pkg_resources.*",
        ".*vtk display not available.*",
        ".*to activate it install python.*",
    ):
        warnings.filterwarnings("ignore", message=pat)

    return _logger


# ── Accesseur global ──────────────────────────────────────────────────────────
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retourne le logger de l'application.
    Si init_logger() n'a pas encore été appelé, initialise avec les
    paramètres par défaut (utile pour les modules importés tôt).

    Args:
        name: Sous-nom optionnel (ex: 'bridge', 'controller').
              Permet de distinguer l'origine dans les logs.
    """
    global _logger
    if _logger is None:
        init_logger()
    if name:
        return _logger.getChild(name)
    return _logger


def get_log_path() -> Optional[Path]:
    """Retourne le chemin du fichier log courant."""
    return _log_path


def get_log_dir() -> Optional[Path]:
    """Retourne le répertoire des logs."""
    return _log_dir


def get_recent_logs(n: int = 10) -> list[Path]:
    """Retourne les n fichiers log les plus récents."""
    if _log_dir is None or not _log_dir.exists():
        return []
    logs = sorted(_log_dir.glob("lmgc90_gui_*.log"), reverse=True)
    return logs[:n]