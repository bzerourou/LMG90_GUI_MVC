"""
examples_dialog.py — Dialogue de sélection et chargement d'un exemple.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QMessageBox, QSplitter, QWidget
)
from PyQt6.QtCore import Qt

from ...examples import EXAMPLES, get_categories, get_example


class ExamplesDialog(QDialog):
    """
    Liste les exemples groupés par catégorie, affiche la description du
    sélectionné, et propose de le charger dans un NOUVEAU projet (l'appelant
    reçoit l'id via self.selected_example_id après exec()==Accepted).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Bibliothèque d'exemples")
        self.resize(760, 480)
        self.selected_example_id: str | None = None

        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Exemple"])
        self.tree.setMinimumWidth(280)
        self.tree.itemClicked.connect(self._on_select)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        splitter.addWidget(self.tree)

        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)

        self.title_label = QLabel("<i>Sélectionnez un exemple à gauche</i>")
        self.title_label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        detail_layout.addWidget(self.title_label)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: #666; font-size: 9pt;")
        detail_layout.addWidget(self.meta_label)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(
            "background: #f0f4f8; padding: 12px; border-radius: 6px;"
        )
        detail_layout.addWidget(self.desc_label)
        detail_layout.addStretch()

        splitter.addWidget(detail_widget)
        splitter.setSizes([280, 480])
        layout.addWidget(splitter)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.load_btn = QPushButton("📂 Charger dans un nouveau projet")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self._on_load)
        btn_row.addWidget(self.load_btn)
        cancel_btn = QPushButton("Fermer")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self._populate_tree()

    def _populate_tree(self):
        cat_items = {}
        for cat in get_categories():
            item = QTreeWidgetItem([cat])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            self.tree.addTopLevelItem(item)
            item.setExpanded(True)
            cat_items[cat] = item

        for ex in EXAMPLES:
            child = QTreeWidgetItem([ex.title])
            child.setData(0, Qt.ItemDataRole.UserRole, ex.id)
            cat_items[ex.category].addChild(child)

    def _on_select(self, item: QTreeWidgetItem, column: int):
        example_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not example_id:
            self.load_btn.setEnabled(False)
            return

        ex = get_example(example_id)
        if not ex:
            return

        self.selected_example_id = example_id
        self.title_label.setText(ex.title)
        self.meta_label.setText(
            f"Dimension : {ex.dimension}D  •  Niveau : {ex.difficulty}  •  "
            f"Tags : {', '.join(ex.tags)}"
        )
        self.desc_label.setText(ex.description)
        self.load_btn.setEnabled(True)

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        if item.data(0, Qt.ItemDataRole.UserRole):
            self._on_load()

    def _on_load(self):
        if not self.selected_example_id:
            return
        ex = get_example(self.selected_example_id)
        reply = QMessageBox.question(
            self, "Charger l'exemple",
            f"Charger « {ex.title} » créera un NOUVEAU projet.\n"
            "Le projet actuel non sauvegardé sera perdu.\n\nContinuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()