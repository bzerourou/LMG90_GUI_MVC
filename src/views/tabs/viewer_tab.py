# ============================================================================
# viewer_tab.py  —  Onglet de visualisation 3D  (MainWindow integration)
# ============================================================================
"""
ViewerTab : wrapper de Viewer3D pour l'intégration dans MainWindow.

Le viewer N'est PAS rafraîchi automatiquement à chaque changement d'état.
L'utilisateur clique sur « 🔄 Rafraîchir la scène » pour déclencher le rendu.
Cela évite les freeze lors de projets volumineux (granulo, maçonnerie).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal

from ...core.particle_population import ParticlePopulation
from ...gui.dialogs.viewer_3d import Viewer3D


class ViewerTab(QWidget):
    """
    Onglet de visualisation 3D intégré dans MainWindow.

    Le rendu est déclenché UNIQUEMENT sur clic du bouton « Rafraîchir ».

    Signaux re-émis
    ───────────────
    avatar_selected(int)    : index de l'avatar cliqué dans la scène
    distance_measured(float): distance mesurée avec le mode Règle
    """

    avatar_selected   = pyqtSignal(int)
    distance_measured = pyqtSignal(float)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller  = controller
        self._dirty      = False   # True = données ont changé depuis le dernier rendu

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Bandeau supérieur ────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 2, 4, 2)

        self._pending_label = QLabel("")
        self._pending_label.setStyleSheet(
            "color: #e8a020; font-size: 9pt; font-style: italic;"
        )
        bar.addWidget(self._pending_label)
        bar.addStretch()

        self._refresh_btn = QPushButton("🔄 Rafraîchir la scène")
        self._refresh_btn.setToolTip(
            "Recharge la visualisation 3D depuis l'état courant du projet.\n"
            "Non automatique pour éviter les freezes sur grands projets."
        )
        self._refresh_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 3px 10px; }"
            "QPushButton:hover { background: #2a5a9a; color: white; }"
        )
        self._refresh_btn.clicked.connect(self._do_refresh)
        bar.addWidget(self._refresh_btn)

        bar_widget = QWidget()
        bar_widget.setLayout(bar)
        bar_widget.setStyleSheet("background: #111122; border-bottom: 1px solid #333;")
        root.addWidget(bar_widget)

        # ── Viewer 3D ────────────────────────────────────────────────────────
        self.viewer = Viewer3D(controller, self)
        root.addWidget(self.viewer, stretch=1)

        # Relayer les signaux Viewer3D
        self.viewer.avatar_clicked.connect(self._on_avatar_clicked)
        self.viewer.measurement_done.connect(self._on_measurement)

    # =========================================================================
    # API publique — appelée par MainWindow._refresh_all()
    # =========================================================================

    def refresh(self):
        """
        Marque la scène comme « en attente de rafraîchissement ».
        Ne déclenche PAS le rendu — l'utilisateur doit cliquer sur le bouton.
        """
        self._dirty = True
        items = [*self.controller.state.avatars, *self.controller.state.particle_populations]
        n = sum(len(item) if isinstance(item, ParticlePopulation) else 1 for item in items)
        self._pending_label.setText(
            f"⚠️ Scène non à jour — {n} objet{'s' if n != 1 else ''} à afficher"
        )
        self._refresh_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 3px 10px; "
            "background: #3a6aaa; color: white; }"
            "QPushButton:hover { background: #4a7abb; color: white; }"
        )

    # =========================================================================
    # Rafraîchissement effectif
    # =========================================================================

    def _do_refresh(self):
        """Recharge la scène 3D depuis les avatars et les populations de particules."""
        renderables = [*self.controller.state.avatars, *self.controller.state.particle_populations]
        self.viewer.update_avatars(renderables)
        self._dirty = False
        self._pending_label.setText("")
        self._refresh_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 3px 10px; }"
            "QPushButton:hover { background: #2a5a9a; color: white; }"
        )

    # =========================================================================
    # Handlers internes
    # =========================================================================

    def _on_avatar_clicked(self, index: int):
        self.avatar_selected.emit(index)

    def _on_measurement(self, dist: float):
        self.distance_measured.emit(dist)