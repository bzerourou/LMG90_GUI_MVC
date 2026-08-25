# src/views/command_bar.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import QStringListModel 

class CommandBar(QWidget):
    """
    Barre de commande texte pour piloter l'interface.
    Émet command_entered(str) à chaque validation — MainWindow interprète.
    """
    command_entered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index = -1
        self._completer_model = QStringListModel()
        self._setup_ui()
        self._setup_completer()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        icon = QLabel("⌘")
        icon.setStyleSheet("font-weight: bold; color: #2a5aaa;")
        layout.addWidget(icon)

        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "Tapez une commande… ex: tab avatar | dim 3 | viewer color type | theme dark"
        )
        self.input.returnPressed.connect(self._on_submit)
        self.input.installEventFilter(self)
        layout.addWidget(self.input, stretch=1)

        run_btn = QPushButton("▶")
        run_btn.setFixedWidth(28)
        run_btn.setToolTip("Exécuter la commande")
        run_btn.clicked.connect(self._on_submit)
        layout.addWidget(run_btn)

        help_btn = QPushButton("?")
        help_btn.setFixedWidth(24)
        help_btn.setToolTip("Aide sur les commandes disponibles")
        help_btn.clicked.connect(lambda: self.command_entered.emit("help"))
        layout.addWidget(help_btn)

        self.setStyleSheet(
            "CommandBar { background:#12203a; border-top:1px solid #2a3a5a; "
            "border-bottom:1px solid #2a3a5a; }"
            "QLineEdit { background:#1a2842; color:#e0e8ff; border:1px solid #345; "
            "border-radius:4px; padding:4px 6px; }"
        )

    def _on_submit(self):
        text = self.input.text().strip()
        if not text:
            return
        self._history.append(text)
        self._history_index = len(self._history)
        self.input.clear()
        self.command_entered.emit(text)

    def eventFilter(self, obj, event):
        # Navigation historique avec ↑ / ↓
        if obj is self.input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up and self._history:
                self._history_index = max(0, self._history_index - 1)
                self.input.setText(self._history[self._history_index])
                return True
            if event.key() == Qt.Key.Key_Down and self._history:
                self._history_index = min(len(self._history), self._history_index + 1)
                if self._history_index == len(self._history):
                    self.input.clear()
                else:
                    self.input.setText(self._history[self._history_index])
                return True
        return super().eventFilter(obj, event)

    def set_status(self, message: str, ok: bool = True):
        color = "#7fd97f" if ok else "#ff8080"
        self.setToolTip(message)
        self.input.setStyleSheet(
            f"QLineEdit {{ background:#1a2842; color:{color}; border:1px solid #345; "
            "border-radius:4px; padding:4px 6px; }"
        )
        
    def _setup_completer(self):
        completer = QCompleter(self._completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)   # filtre "contient", pas juste préfixe
        self.input.setCompleter(completer)
        self._completer = completer

    def set_suggestions(self, suggestions: list[str]):
        """Met à jour la liste de complétion (appelée par MainWindow)."""
        self._completer_model.setStringList(suggestions)