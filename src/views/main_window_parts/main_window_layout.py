"""Construction de la disposition principale de la fenetre."""
from PyQt6.QtWidgets import (
    QDockWidget, QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton,
)
from PyQt6.QtCore import Qt

from ..tree_view import ModelTreeView
from ..command_bar import CommandBar


class MainWindowLayoutMixin:
    """Construit le dock, les zones centrales et le rendu."""

    def _create_tree_dock(self):
        """Cree le dock contenant l'arbre du modele."""
        dock = QDockWidget("Arbre du modele", self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self.tree_view = ModelTreeView(self.controller)
        dock.setWidget(self.tree_view.tree)
        dock.setMinimumWidth(400)
        self.tree_view.item_selected.connect(self._on_tree_item_selected)

    def _create_central_area(self):
        """Cree le splitter principal et ses trois zones."""
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(splitter)

        self._create_tabs()
        splitter.addWidget(self.tabs)

        self._create_render_widget()
        splitter.addWidget(self.render_widget)

        self.command_bar = CommandBar()
        self.command_bar.command_entered.connect(self._on_command_entered)
        splitter.addWidget(self.command_bar)
        splitter.setSizes([800, 50, 50])

    def _create_render_widget(self):
        """Cree la zone de visualisation inferieure."""
        self.render_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        viz_group = QGroupBox("Visualisation et Rendu")
        viz_layout = QHBoxLayout()

        lmgc_button = QPushButton("LMGC90 Visualisation")
        lmgc_button.setToolTip("Visualise les avatars crees")
        lmgc_button.setMinimumHeight(40)
        lmgc_button.clicked.connect(self._on_lmgc_visualization)
        viz_layout.addWidget(lmgc_button)

        paraview_button = QPushButton("Ouvrir ParaView")
        paraview_button.setToolTip("Ouvre les resultats de simulation")
        paraview_button.setMinimumHeight(40)
        paraview_button.clicked.connect(self._on_paraview)
        viz_layout.addWidget(paraview_button)

        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)
        self.render_widget.setLayout(layout)
        self.render_widget.setMinimumHeight(150)
