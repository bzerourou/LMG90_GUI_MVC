
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QGroupBox, QTextEdit, QProgressBar, QLabel
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSignal as Signal
from ...core.validators import ValidationError
import subprocess
import sys

class ComputeWorker(QThread):
    """Thread pour exécuter le calcul"""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, script_path, work_dir):  # ✅ Ajouter work_dir
        super().__init__()
        self.script_path = script_path
        self.work_dir = work_dir  # ✅ Stocker
    
    def run(self):
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.script_path)],
                cwd=str(self.work_dir),  # ✅ Définir le répertoire de travail
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                self.progress.emit(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                self.finished.emit(True, "✅ Calcul terminé avec succès")
            else:
                self.finished.emit(False, f"❌ Erreur code {process.returncode}")
        
        except Exception as e:
            self.finished.emit(False, f"❌ Exception: {e}")


class ComputeTab(QWidget):
    """Onglet paramètres de calcul"""
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.worker = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Paramètres temporels
        time_group = QGroupBox("⏱️ Paramètres Temporels")
        time_form = QFormLayout()
        
        self.dt_input = QLineEdit("1e-3")
        time_form.addRow("Pas de temps (dt):", self.dt_input)
        
        self.nb_steps_input = QLineEdit("1000")
        time_form.addRow("Nombre d'itérations:", self.nb_steps_input)
        
        self.theta_input = QLineEdit("0.5")
        time_form.addRow("Theta intégrateur:", self.theta_input)
        
        time_group.setLayout(time_form)
        layout.addWidget(time_group)
        
        # Paramètres solveur
        solver_group = QGroupBox("🔧 Paramètres Solveur")
        solver_form = QFormLayout()
        
        self.tol_input = QLineEdit("1.666e-4")
        solver_form.addRow("Tolérance:", self.tol_input)
        
        self.relax_input = QLineEdit("1.0")
        solver_form.addRow("Relaxation:", self.relax_input)
        
        self.norm_combo = QComboBox()
        self.norm_combo.addItems(["Quad ", "QM   ", "Maxim"])
        solver_form.addRow("Norme:", self.norm_combo)
        
        self.gs_it1_input = QLineEdit("50")
        solver_form.addRow("Itérations GS1:", self.gs_it1_input)
        
        self.gs_it2_input = QLineEdit("1000")
        solver_form.addRow("Itérations GS2:", self.gs_it2_input)
        
        self.solver_combo = QComboBox()
        self.solver_combo.addItems([
            "Stored_Delassus_Loops         ",
            "Exchange_Local_Global         ",
            "Conjugate_Gradient            "
        ])
        solver_form.addRow("Type solveur:", self.solver_combo)
        
        solver_group.setLayout(solver_form)
        layout.addWidget(solver_group)
        
        # Paramètres sortie
        output_group = QGroupBox("💾 Sorties")
        output_form = QFormLayout()
        
        self.freq_write_input = QLineEdit("50")
        output_form.addRow("Fréquence écriture:", self.freq_write_input)
        
        self.freq_display_input = QLineEdit("50")
        output_form.addRow("Fréquence affichage:", self.freq_display_input)
        
        output_group.setLayout(output_form)
        layout.addWidget(output_group)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Console de sortie
        layout.addWidget(QLabel("<b>📋 Console:</b>"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace;")
        layout.addWidget(self.console)
        
        # Boutons
        btn_layout = QVBoxLayout()
        
        self.run_btn = QPushButton("▶️ Lancer le Calcul")
        self.run_btn.clicked.connect(self.run_computation)
        btn_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_computation)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def get_parameters(self):
        """Retourne les paramètres de calcul"""
        return {
            'dt': float(self.dt_input.text()),
            'nb_steps': int(self.nb_steps_input.text()),
            'theta': float(self.theta_input.text()),
            'tol': float(self.tol_input.text()),
            'relax': float(self.relax_input.text()),
            'norm': self.norm_combo.currentText(),
            'gs_it1': int(self.gs_it1_input.text()),
            'gs_it2': int(self.gs_it2_input.text()),
            'solver_type': self.solver_combo.currentText(),
            'freq_write': int(self.freq_write_input.text()),
            'freq_display': int(self.freq_display_input.text()),
        }
    
    def run_computation(self):
        """Lance le calcul"""
        try:

            params = self.get_parameters()
            if params['dt'] <= 0:
                raise ValidationError("Le pas de temps doit être > 0")
            
            if params['nb_steps'] <= 0:
                raise ValidationError("Le nombre d'itérations doit être > 0")
            
            if params['tol'] <= 0:
                raise ValidationError("La tolérance doit être > 0")
            
            if params['gs_it1'] <= 0 or params['gs_it2'] <= 0:
                raise ValidationError("Les itérations GS doivent être > 0")
            #  S'assurer que le répertoire de travail est correct
            work_dir = self.controller.project_path.parent
            
            # Générer DATBOX
            datbox_path = work_dir / "DATBOX"
            self.controller.generate_datbox(datbox_path)
            
            # Générer script
            script_path = work_dir / "command.py"
            from ...utils.compute_script_generator import ComputeScriptGenerator
            generator = ComputeScriptGenerator(self.controller)
            generator.generate(script_path, params)
            
            # Lancer le worker avec le bon répertoire de travail
            self.console.clear()
            self.console.append(">>> Démarrage du calcul...\n")
            
            self.worker = ComputeWorker(script_path, work_dir)  
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_finished)
            self.worker.start()
            
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Lancement échoué:\n{e}")
    
    def stop_computation(self):
        """Arrête le calcul"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.console.append("\n⚠️ Calcul interrompu par l'utilisateur")
            self.on_finished(False, "Interrompu")
    
    def on_progress(self, line):
        """Affiche la progression"""
        self.console.append(line)
    
    def on_finished(self, success, message):
        """Calcul terminé"""
        self.console.append(f"\n{message}")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Succès", message)
        else:
            QMessageBox.warning(self, "Échec", message)
    
    def refresh(self):
        """Rafraîchit (appelé par main_window)"""
        pass