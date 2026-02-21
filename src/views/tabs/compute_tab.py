from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QGroupBox, QTextEdit, QProgressBar, QLabel, 
    QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from ...core.validators import ValidationError
import sys
import os
from pathlib import Path
from io import StringIO


class ComputeWorker(QThread):
    """Thread pour exécuter le calcul dans un subprocess externe sans fenêtre"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, script_path, work_dir):
        super().__init__()
        self.script_path = script_path
        self.work_dir = work_dir
        self._process = None
        self._stop_requested = False

    def run(self):
        """Lance command.py dans un subprocess sans fenêtre (Windows-safe)"""
        import subprocess

        self.progress.emit(f"📁 Répertoire de travail : {self.work_dir}")
        self.progress.emit(f"📄 Script : {self.script_path}")
        self.progress.emit("=" * 60)

        try:
            # En mode frozen, sys.executable est LMGC90_GUI.exe qui embarque
            # python + toutes les libs. On le relance avec LMGC90_WORKER=<script>
            # dans l'env : main.py détecte cette variable et exécute le script
            # directement sans lancer la GUI.
            # En mode dev, sys.executable est python.exe normal.
            exe = sys.executable
            env = os.environ.copy()
            env.pop("PYTHONHOME", None)

            if getattr(sys, 'frozen', False):
                cmd = [exe]
                env["LMGC90_WORKER"] = str(self.script_path)
            else:
                cmd = [exe, "-u", str(self.script_path)]

            self.progress.emit(f"🐍 Exécutable : {exe}")

            kwargs = {}
            if sys.platform == "win32":
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(
                cmd,
                cwd=str(self.work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                **kwargs
            )

            # Lire en temps réel
            for line in iter(self._process.stdout.readline, ''):
                if self._stop_requested:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                    self.finished.emit(False, "Interrompu par l'utilisateur")
                    return
                stripped = line.rstrip()
                if stripped:
                    self.progress.emit(stripped)

            self._process.wait()
            returncode = self._process.returncode

            self.progress.emit("=" * 60)

            if returncode == 0:
                self.finished.emit(True, "✅ Calcul terminé avec succès")
            else:
                # Abort Fortran (STOP 1) → returncode != 0
                self.progress.emit(f"⚠️ Le calcul s'est arrêté (code retour : {returncode})")
                self.progress.emit("Consultez les messages ci-dessus pour le détail de l'erreur.")
                self.finished.emit(False, f"Arrêt anormal (code {returncode})")

        except Exception as e:
            self.progress.emit(f"❌ Erreur lancement : {type(e).__name__}: {e}")
            import traceback
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.progress.emit(line)
            self.finished.emit(False, f"❌ {e}")

    def stop(self):
        """Arrête le calcul"""
        self._stop_requested = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except Exception:
                self._process.kill()


class ComputeTab(QWidget):
    """Onglet paramètres de calcul"""
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.worker = None
        self._setup_ui()
    
    def _setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Créer une zone de défilement
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget contenant tout le contenu
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)

        title = QLabel("<h2>⚙️ Configuration du Calcul</h2>")
        layout.addWidget(title)
        
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
        
        self.disable_log_check = QCheckBox("Désactiver les messages chipy (chipy.utilities_DisableLogMes)")
        self.disable_log_check.setChecked(False)
        output_form.addRow("", self.disable_log_check)
        
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
        self.console.setStyleSheet(
            "background-color: #1e1e1e; "
            "color: #d4d4d4; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 9pt; "
            "padding: 8px;"
        )
        self.console.setMinimumHeight(300)
        layout.addWidget(self.console)
        
        # Boutons
        btn_layout = QVBoxLayout()
        
        self.run_btn = QPushButton("▶️ Lancer le Calcul")
        self.run_btn.setStyleSheet("font-weight: bold; padding: 10px; font-size: 11pt;")
        self.run_btn.clicked.connect(self.run_computation)
        btn_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter le calcul")
        self.stop_btn.setStyleSheet("padding: 10px; font-size: 11pt;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_computation)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # Configurer le scroll
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)

    
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
            'disable_log': self.disable_log_check.isChecked(),
        }
    
    def run_computation(self):
        """Lance le calcul avec protection totale contre les erreurs"""

        if not self.controller.project_path: 
            QMessageBox.warning(
                self, 
                "Projet non sauvegardé",
                "Veuillez d'abord sauvegarder le projet avant de lancer le calcul."
            )
            return
        
        try:
            # Valider les paramètres
            params = self.get_parameters()
            if params['dt'] <= 0:
                raise ValidationError("Le pas de temps doit être > 0")
            
            if params['nb_steps'] <= 0:
                raise ValidationError("Le nombre d'itérations doit être > 0")
            
            if params['tol'] <= 0:
                raise ValidationError("La tolérance doit être > 0")
            
            if params['gs_it1'] <= 0 or params['gs_it2'] <= 0:
                raise ValidationError("Les itérations GS doivent être > 0")
            
            # S'assurer que le répertoire de travail est correct
            work_dir = self.controller.project_path.parent
            
            # Générer DATBOX
            self.console.clear()
            self.console.append("🔧 Préparation du calcul...")
            self.console.append("")
            
            datbox_path = work_dir / "DATBOX"
            self.controller.generate_datbox(datbox_path)
            self.console.append(f"✅ DATBOX généré : {datbox_path}")
            
            # Générer script
            script_path = work_dir / "command.py"
            from ...utils.compute_script_generator import ComputeScriptGenerator
            generator = ComputeScriptGenerator(self.controller)
            generator.generate(script_path, params)
            self.console.append(f"✅ Script généré : {script_path}")
            
            # Vérifier que le script existe
            if not script_path.exists():
                raise FileNotFoundError(f"Le script n'a pas été créé : {script_path}")
            
            self.console.append("")
            self.console.append("=" * 60)
            self.console.append("🚀 DÉMARRAGE DU CALCUL")
            self.console.append("=" * 60)
            self.console.append("")
            
            # Lancer le worker
            self.worker = ComputeWorker(script_path, work_dir)
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_finished)
            self.worker.start()
            
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Mode indéterminé
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            error_msg = f"Erreur lors de la préparation:\n{e}"
            self.console.append(f"\n❌ {error_msg}")
            QMessageBox.critical(self, "Erreur", error_msg)
            
            # Afficher la traceback dans la console
            import traceback
            self.console.append("\nTraceback:")
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.console.append(line)
    
    def stop_computation(self):
        """Arrête le calcul"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmer l'arrêt",
                "Voulez-vous vraiment arrêter le calcul en cours ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.console.append("\n⚠️ Arrêt demandé par l'utilisateur...")
                self.worker.stop()
                self.worker.wait(3000)  # Attendre max 3 secondes
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait()
                self.console.append("⚠️ Calcul interrompu")
                self.on_finished(False, "Interrompu par l'utilisateur")
    
    def on_progress(self, line):
        """Affiche la progression dans la console"""
        self.console.append(line)
        
        # Auto-scroll vers le bas
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_finished(self, success, message):
        """Calcul terminé - Aucun crash possible ici"""
        self.console.append("")
        self.console.append("=" * 60)
        self.console.append(f"📊 RÉSULTAT : {message}")
        self.console.append("=" * 60)
        
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Scroll vers le bas pour voir le résultat
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Message non-bloquant pour l'utilisateur
        if success:
            QMessageBox.information(
                self, 
                "✅ Succès", 
                "Le calcul s'est terminé avec succès !\n\n"
                "Consultez la console pour les détails."
            )
        else:
            # Même en cas d'erreur, on ne crash pas !
            QMessageBox.warning(
                self, 
                "⚠️ Erreur", 
                f"Le calcul a rencontré une erreur.\n\n"
                "Consultez la console pour les détails de l'erreur."
            )
    
    def refresh(self):
        """Rafraîchit (appelé par main_window)"""
        pass