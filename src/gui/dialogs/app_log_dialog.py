# ============================================================================
# app_log_dialog.py  —  Fenêtre de visualisation du journal de l'application
# ============================================================================
"""
Dialogue non-modal affichant le fichier log courant de LMGC90_GUI
avec :
  - colorisation syntaxique (erreurs, warnings, infos, debug)
  - champ de filtre temps réel
  - sélection d'une session précédente
  - bouton de sauvegarde et d'ouverture dans l'éditeur système
  - rafraîchissement automatique toutes les 3 s
"""
import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter, QTextDocument

from ...core.app_logger import get_log_path, get_log_dir, get_recent_logs


# ── Colorisation syntaxique ───────────────────────────────────────────────────
class _LogHighlighter(QSyntaxHighlighter):
    """Colorie chaque ligne selon son niveau de log."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._rules: list = []

        def _rule(pattern: str, r: int, g: int, b: int, bold: bool = False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(r, g, b))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            import re
            self._rules.append((re.compile(pattern, re.IGNORECASE), fmt))

        # Niveaux de log standard
        _rule(r'\[CRITICAL\]',  255,  60,  60, bold=True)
        _rule(r'\[ERROR   \]',  255, 100,  80, bold=True)
        _rule(r'\[WARNING \]',  255, 200,  50)
        _rule(r'\[INFO    \]',  130, 200, 130)
        _rule(r'\[DEBUG   \]',  120, 160, 200)

        # Mots-clés d'erreur dans les messages
        _rule(r'.*(exception|traceback|error|erreur|critical|failed|failure).*',
              255, 120, 100)
        # Mots-clés de warning
        _rule(r'.*(warning|warn|attention|deprecated).*', 255, 210, 80)
        # Succès
        _rule(r'.*(✅|terminé|success|démarr|ready|ok\b).*', 100, 220, 120)
        # En-têtes de session (lignes de =)
        _rule(r'^={10,}', 100, 100, 120)
        # Horodatages
        _rule(r'^\d{4}-\d{2}-\d{2}', 160, 160, 160)
        # Noms de modules (bridge, controller, etc.)
        _rule(r'lmgc90_gui\.\w+', 160, 200, 255)

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            if pattern.search(text):
                self.setFormat(0, len(text), fmt)
                return


# ── Dialogue principal ────────────────────────────────────────────────────────
class AppLogDialog(QDialog):
    """
    Fenêtre non-modale affichant le journal de l'application.
    Se rafraîchit automatiquement pendant que l'app tourne.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Journal de l'application — LMGC90_GUI")
        self.setMinimumSize(900, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint
        )

        self._current_path: Path | None = get_log_path()
        self._all_lines: list[str]      = []

        self._setup_ui()
        self._load_sessions()

        # Rafraîchissement automatique toutes les 3 s
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self.reload)
        self._timer.start()

        self.reload()

    # ── Interface ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── Barre supérieure : sélection session + filtre ─────────────────────
        top = QHBoxLayout()

        top.addWidget(QLabel("Session :"))
        self._session_combo = QComboBox()
        self._session_combo.setMinimumWidth(320)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        top.addWidget(self._session_combo)

        top.addStretch()

        top.addWidget(QLabel("🔍"))
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrer par mot-clé…")
        self._filter.setMaximumWidth(220)
        self._filter.textChanged.connect(self._apply_filter)
        top.addWidget(self._filter)

        top.addWidget(QLabel("Niveau min :"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(["TOUT", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self._level_combo.currentTextChanged.connect(lambda _: self._apply_filter(self._filter.text()))
        top.addWidget(self._level_combo)

        layout.addLayout(top)

        # ── Zone de texte ─────────────────────────────────────────────────────
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(
            "background-color: #0d1117;"
            "color: #c9d1d9;"
            "font-family: 'Consolas', 'Courier New', monospace;"
            "font-size: 9pt;"
            "padding: 8px;"
        )
        self._highlighter = _LogHighlighter(self._text.document())
        layout.addWidget(self._text)

        # ── Barre inférieure : statut + boutons ───────────────────────────────
        bot = QHBoxLayout()

        self._status = QLabel("Chargement…")
        self._status.setStyleSheet("color: #888; font-size: 8pt;")
        bot.addWidget(self._status, stretch=1)

        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self.reload)
        bot.addWidget(refresh_btn)

        save_btn = QPushButton("💾 Sauvegarder sous…")
        save_btn.clicked.connect(self._save_as)
        bot.addWidget(save_btn)

        open_btn = QPushButton("📂 Ouvrir dans l'éditeur")
        open_btn.clicked.connect(self._open_in_editor)
        bot.addWidget(open_btn)

        open_dir_btn = QPushButton("📁 Ouvrir dossier logs")
        open_dir_btn.clicked.connect(self._open_log_dir)
        bot.addWidget(open_dir_btn)

        close_btn = QPushButton("✖ Fermer")
        close_btn.clicked.connect(self.hide)
        bot.addWidget(close_btn)

        layout.addLayout(bot)

    # ── Chargement des sessions ───────────────────────────────────────────────
    def _load_sessions(self):
        """Remplit le combo avec les fichiers log récents."""
        self._session_combo.blockSignals(True)
        self._session_combo.clear()

        logs = get_recent_logs(n=15)
        for p in logs:
            label = p.name  # ex: lmgc90_gui_20250301_143022.log
            self._session_combo.addItem(label, userData=p)

        # Sélectionner la session courante
        current = get_log_path()
        if current:
            for i in range(self._session_combo.count()):
                if self._session_combo.itemData(i) == current:
                    self._session_combo.setCurrentIndex(i)
                    break

        self._session_combo.blockSignals(False)

    def _on_session_changed(self, index: int):
        """Change de fichier log."""
        path = self._session_combo.itemData(index)
        if path and Path(path).exists():
            self._current_path = Path(path)
            self._all_lines = []
            self.reload()

    # ── Chargement / affichage ────────────────────────────────────────────────
    def reload(self):
        """Relit le fichier log depuis le disque."""
        if not self._current_path or not self._current_path.exists():
            self._status.setText("⚠️ Fichier log introuvable")
            return
        try:
            with open(self._current_path, 'r', encoding='utf-8', errors='replace') as f:
                self._all_lines = f.readlines()
            self._apply_filter(self._filter.text())

            size_kb = self._current_path.stat().st_size // 1024
            self._status.setText(
                f"{self._current_path.name}  —  "
                f"{len(self._all_lines)} lignes  —  {size_kb} Ko"
            )
        except Exception as e:
            self._status.setText(f"❌ Erreur : {e}")

    def _apply_filter(self, keyword: str):
        """Filtre les lignes selon le mot-clé et le niveau minimum."""
        kw    = keyword.strip().lower()
        level = self._level_combo.currentText()

        # Niveaux à afficher
        _order = {"TOUT": 0, "DEBUG": 10, "INFO": 20,
                  "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        min_lvl = _order.get(level, 0)

        _tag_lvl = {
            "[DEBUG   ]": 10, "[INFO    ]": 20,
            "[WARNING ]": 30, "[ERROR   ]": 40, "[CRITICAL]": 50,
        }

        lines = self._all_lines

        # Filtre niveau
        if min_lvl > 0:
            filtered = []
            for l in lines:
                line_lvl = 0
                for tag, lvl in _tag_lvl.items():
                    if tag in l:
                        line_lvl = lvl
                        break
                if line_lvl >= min_lvl:
                    filtered.append(l)
            lines = filtered

        # Filtre mot-clé
        if kw:
            lines = [l for l in lines if kw in l.lower()]

        self._text.setPlainText("".join(lines))
        # Auto-scroll vers la fin
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Actions ───────────────────────────────────────────────────────────────
    def _save_as(self):
        if not self._current_path:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder le log",
            str(self._current_path.parent / self._current_path.name),
            "Fichiers log (*.log *.txt);;Tous (*)"
        )
        if dest:
            Path(dest).write_text("".join(self._all_lines), encoding='utf-8')

    def _open_in_editor(self):
        if not self._current_path or not self._current_path.exists():
            return
        import subprocess
        if sys.platform == "win32":
            subprocess.Popen(["notepad", str(self._current_path)])
        else:
            subprocess.Popen(["xdg-open", str(self._current_path)])

    def _open_log_dir(self):
        d = get_log_dir()
        if not d or not d.exists():
            return
        import subprocess
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(d)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(d)])
        else:
            subprocess.Popen(["xdg-open", str(d)])

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)