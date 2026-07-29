# ============================================================================
# quick_material_model.py — Dialogues de création rapide Matériau / Modèle
# ============================================================================
"""
Boîtes de dialogue simplifiées, partagées entre plusieurs wizards
(FactoryWizard, GranuloFastDialog, ...) pour créer rapidement un matériau
ou un modèle de base sans passer par les onglets complets.

Auparavant dupliquées à l'identique dans factory_wizard.py et
fast_granulo_dialg.py — centralisées ici pour éviter la divergence de code
lors des futures évolutions (ex: nouveaux champs de matériau).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QLabel, QDialogButtonBox
)

from ...core.models import Material, MaterialType, Model


_STYLE_QUICK_ADD_BTN = """
    QToolButton {
        font-size: 12pt;
        font-weight: bold;
        padding: 0px;
        border: 1px solid #3a5a9a;
        border-radius: 4px;
        background: #eef3ff;
        color: #2a4a8a;
        min-width: 26px;
        min-height: 26px;
        max-width: 26px;
        max-height: 26px;
    }
    QToolButton:hover {
        background: #2a5aaa;
        color: white;
    }
"""


def _dbl(value: float, minimum: float = 0., maximum: float = 1e6,
         decimals: int = 4, step: float = 0.001):
    from PyQt6.QtWidgets import QDoubleSpinBox
    sb = QDoubleSpinBox()
    sb.setRange(minimum, maximum)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setValue(value)
    return sb


def make_quick_add_button(tooltip: str):
    """Crée un petit bouton ➕ standard pour création rapide à côté d'une combobox."""
    from PyQt6.QtWidgets import QToolButton
    btn = QToolButton()
    btn.setText("➕")
    btn.setToolTip(tooltip)
    btn.setStyleSheet(_STYLE_QUICK_ADD_BTN)
    return btn


class QuickMaterialDialog(QDialog):
    """Boîte de dialogue simplifiée pour créer un matériau de base (RIGID ou ELAS)."""

    def __init__(self, parent=None, name_max_length: int = 5):
        super().__init__(parent)
        self.setWindowTitle("➕ Nouveau matériau simple")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit("TDURx")
        self.name_input.setMaxLength(name_max_length)
        form.addRow("Nom :", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["RIGID (corps rigide)", "ELAS (élastique)"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type :", self.type_combo)

        self.density = _dbl(2500., 0., 1e9, 2, 10.0)
        form.addRow("Densité (kg/m³) :", self.density)

        self.young = _dbl(7.0e10, 0., 1e15, 1, 1e8)
        self._young_label = QLabel("Module de Young (Pa) :")
        form.addRow(self._young_label, self.young)

        self.poisson = _dbl(0.3, 0., 0.5, 3, 0.01)
        self._poisson_label = QLabel("Coefficient de Poisson :")
        form.addRow(self._poisson_label, self.poisson)

        layout.addLayout(form)

        hint = QLabel(
            "💡 Crée un matériau minimal. Pour des propriétés avancées, "
            "utilisez l'onglet Matériaux du projet."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #607090; font-size: 9pt; padding: 0 14px 6px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_type_changed(0)

    def _on_type_changed(self, idx: int):
        is_elas = (idx == 1)
        self._young_label.setVisible(is_elas)
        self.young.setVisible(is_elas)
        self._poisson_label.setVisible(is_elas)
        self.poisson.setVisible(is_elas)

    def get_material(self) -> Material:
        name = self.name_input.text().strip() or "TDURx"
        if self.type_combo.currentIndex() == 0:
            return Material(
                name=name,
                material_type=MaterialType.RIGID,
                density=self.density.value(),
            )
        return Material(
            name=name,
            material_type=MaterialType.ELAS,
            density=self.density.value(),
            properties={
                'MatProp': {
                    'young': self.young.value(),
                    'nu': self.poisson.value(),
                }
            },
        )


class QuickModelDialog(QDialog):
    """Boîte de dialogue simplifiée pour créer un modèle de corps rigide de base."""

    def __init__(self, dimension: int = 3, parent=None, name_max_length: int = 5):
        super().__init__(parent)
        self.setWindowTitle("➕ Nouveau modèle simple")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit("rigid")
        self.name_input.setMaxLength(name_max_length)
        form.addRow("Nom :", self.name_input)

        self.dim_combo = QComboBox()
        self.dim_combo.addItems(["3D", "2D"])
        self.dim_combo.setCurrentIndex(0 if dimension == 3 else 1)
        form.addRow("Dimension :", self.dim_combo)

        layout.addLayout(form)

        hint = QLabel(
            "💡 Crée un modèle rigide standard (MECAx / Rxx2D ou Rxx3D), "
            "suffisant pour la plupart des avatars rigides."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #607090; font-size: 9pt; padding: 0 14px 6px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_model(self) -> Model:
        name = self.name_input.text().strip() or "rigid"
        dim = 3 if self.dim_combo.currentIndex() == 0 else 2
        element = "Rxx3D" if dim == 3 else "Rxx2D"
        return Model(
            name=name,
            physics="MECAx",
            element=element,
            dimension=dim,
        )