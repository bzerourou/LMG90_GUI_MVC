"""
synchroniser les unités avec le ProjectPreferences.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel


class UnitField(QWidget):
    """
    Usage :
        self.density_input = UnitField(default="2800", unit_key="density")
        form.addRow("Densité :", self.density_input)
        ...
        density = self.eval_float(self.density_input.text(), default=2800, field_name="Densité")
        self.density_input.setText(str(material.density))
    Expose .text() / .setText() / .textChanged — donc drop-in replacement
    de QLineEdit dans le code existant (aucun autre changement requis).
    """

    def __init__(self, default: str = "", unit_key: str = None, parent=None):
        super().__init__(parent)
        self.unit_key = unit_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.line_edit = QLineEdit(default)
        layout.addWidget(self.line_edit)

        self.unit_label = QLabel("")
        self.unit_label.setStyleSheet("color: #777; font-size: 8pt;")
        self.unit_label.setMinimumWidth(45)
        layout.addWidget(self.unit_label)

        self.textChanged = self.line_edit.textChanged  # proxy signal

    # ── API drop-in QLineEdit ────────────────────────────────────────────
    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, value: str):
        self.line_edit.setText(value)

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)

    def setMaxLength(self, n: int):
        self.line_edit.setMaxLength(n)

    # ── Unité ────────────────────────────────────────────────────────────
    def set_unit_label(self, text: str):
        self.unit_label.setText(text)


def apply_unit(field: UnitField, controller):
    """À appeler dans refresh() : met à jour le label depuis les préférences."""
    if field.unit_key:
        labels = controller.state.preferences.get_unit_labels()
        field.set_unit_label(labels.get(field.unit_key, ""))