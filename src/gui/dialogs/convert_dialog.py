from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QMessageBox, QLineEdit, QHBoxLayout
)
from pathlib import Path

from ...core.convert import Converter   # adapte le chemin

class ConvertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convertir script pylmgc90 → .lmgc90")
        self.setMinimumWidth(500)

        self.input_path = QLineEdit()
        self.output_path = QLineEdit()

        layout = QVBoxLayout()

        # Input
        layout.addWidget(QLabel("Script Python à convertir :"))
        h1 = QHBoxLayout()
        btn_browse_in = QPushButton("Parcourir")
        btn_browse_in.clicked.connect(self._browse_input)
        h1.addWidget(self.input_path)
        h1.addWidget(btn_browse_in)
        layout.addLayout(h1)

        # Output
        layout.addWidget(QLabel("Fichier de sortie (.lmgc90) :"))
        h2 = QHBoxLayout()
        btn_browse_out = QPushButton("Parcourir")
        btn_browse_out.clicked.connect(self._browse_output)
        h2.addWidget(self.output_path)
        h2.addWidget(btn_browse_out)
        layout.addLayout(h2)

        # Bouton convert
        self.btn_convert = QPushButton("🚀 Convertir")
        self.btn_convert.clicked.connect(self._convert)
        layout.addWidget(self.btn_convert)

        self.setLayout(layout)

    def _browse_input(self):
        file, _ = QFileDialog.getOpenFileName(self, "Choisir script", "", "*.py")
        if file:
            self.input_path.setText(file)

    def _browse_output(self):
        file, _ = QFileDialog.getSaveFileName(self, "Sortie", "", "*.lmgc90")
        if file:
            self.output_path.setText(file)

    def _convert(self):
        try:
            script = Path(self.input_path.text())
            output = Path(self.output_path.text())

            if not script.exists():
                raise Exception("Fichier script introuvable")

            conv = Converter(script)
            conv.run()

            data = conv.to_lmgc90_dict()

            import json
            output.write_text(json.dumps(data, indent=2))

            QMessageBox.information(self, "Succès", "Conversion terminée ✅")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))