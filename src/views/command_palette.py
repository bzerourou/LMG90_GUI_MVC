# src/views/command_palette.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal


class CommandPalette(QDialog):
    """
    Palette de commandes filtrable (Ctrl+K), inspirée de VSCode.
    command_selected(str) est émis quand l'utilisateur valide une entrée.
    """
    command_selected = pyqtSignal(str)

    def __init__(self, entries: list[tuple[str, str]], parent=None):
        """
        entries: liste de (commande, description)
                 ex: ("tab avatar", "Ouvrir l'onglet Avatar")
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(560, 380)

        self._entries = entries

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.setStyleSheet("""
            QDialog { background:#141e33; border:1px solid #3a5a9a; border-radius:8px; }
            QLineEdit { background:#1e2a45; color:#e8eeff; border:1px solid #345;
                        border-radius:5px; padding:8px 10px; font-size:11pt; }
            QListWidget { background:#141e33; color:#dfe6f7; border:none;
                          font-size:10pt; outline:none; }
            QListWidget::item { padding:6px 8px; border-radius:4px; }
            QListWidget::item:selected { background:#2a5aaa; color:white; }
            QLabel#hint { color:#7a90c0; font-size:8pt; padding:2px 4px; }
        """)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Tapez pour filtrer les commandes…")
        self.search.textChanged.connect(self._on_filter_changed)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemActivated.connect(self._on_activate)
        self.list.installEventFilter(self)
        layout.addWidget(self.list, stretch=1)

        hint = QLabel("↑↓ naviguer   ⏎ exécuter   Échap fermer")
        hint.setObjectName("hint")
        layout.addWidget(hint)

        self._populate("")
        self.search.setFocus()

    # ── Filtrage ──────────────────────────────────────────────────────────
    def _on_filter_changed(self, text: str):
        self._populate(text)

    def _populate(self, filter_text: str):
        self.list.clear()
        needle = filter_text.lower().strip()
        for cmd, desc in self._entries:
            haystack = f"{cmd} {desc}".lower()
            if needle and not all(tok in haystack for tok in needle.split()):
                continue
            item = QListWidgetItem(f"{cmd}   —   {desc}")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self.list.addItem(item)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    # ── Activation ────────────────────────────────────────────────────────
    def _on_activate(self, item: QListWidgetItem):
        cmd = item.data(Qt.ItemDataRole.UserRole)
        self.command_selected.emit(cmd)
        self.close()

    # ── Navigation clavier depuis le champ de recherche ─────────────────────
    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.close()
                return True
            if key == Qt.Key.Key_Down:
                row = min(self.list.currentRow() + 1, self.list.count() - 1)
                self.list.setCurrentRow(row)
                return True
            if key == Qt.Key.Key_Up:
                row = max(self.list.currentRow() - 1, 0)
                self.list.setCurrentRow(row)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.list.currentItem()
                if item:
                    self._on_activate(item)
                return True
        return super().eventFilter(obj, event)