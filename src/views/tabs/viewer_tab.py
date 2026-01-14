

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal

from ...gui.dialogs.viewer_3d import Viewer3D
from ...controllers.project_controller import ProjectController


class ViewerTab(QWidget):
    """Onglet de visualisation 3D"""
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Info
        info = QLabel(
            "<b>🎨 Visualisation 3D Interactive</b><br>"
            "<i>• Clic gauche + glisser : rotation<br>"
            "• Molette : zoom<br>"
            "• Clic droit + glisser : translation</i>"
        )
        info.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info)
        
        # Viewer 3D
        self.viewer = Viewer3D(self.controller)
        layout.addWidget(self.viewer)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("💾 Exporter Image")
        export_btn.clicked.connect(self._on_export_image)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def refresh(self):
        """Rafraîchit la visualisation"""
        avatars = self.controller.state.avatars
        self.viewer.update_avatars(avatars)
    
    def _on_export_image(self):
        """Exporte une capture d'écran"""
        from PyQt6.QtWidgets import QFileDialog
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Exporter Image",
            "screenshot.png",
            "Images (*.png *.jpg)"
        )
        
        if filepath:
            self.viewer.plotter.screenshot(filepath)
            QMessageBox.information(self, "Succès", f"Image exportée:\n{filepath}")