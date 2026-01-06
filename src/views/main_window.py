"""
Fenêtre principale de l'application.
Interface entre l'utilisateur et le contrôleur.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QPushButton, QDockWidget,
    QTreeWidget, QTabWidget, QMessageBox, QFileDialog, QApplication,
    QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from pathlib import Path

from ..controllers.project_controller import ProjectController
from ..core.models import ValidationError
from .tabs import (
    MaterialTab, ModelTab, AvatarTab, EmptyAvatarTab, LoopTab,
    GranuloTab, DOFTab, ContactTab, VisibilityTab, PostProTab
)
from .tree_view import ModelTreeView


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""
    
    # Signaux
    project_loaded = pyqtSignal()
    project_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Contrôleur
        self.controller = ProjectController()
        
        # Configuration fenêtre
        self.setWindowTitle(f"LMGC90_GUI v0.2.5 - {self.controller.state.name}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Interface
        self._setup_ui()
        self._connect_signals()
        
        # État initial
        self.statusBar().showMessage("Prêt", 3000)
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Menu
        self._create_menu()
        
        # Toolbar
        self._create_toolbar()
        
        # Arbre du modèle (dock gauche)
        self._create_tree_dock()
        
        # Zone centrale avec splitter
        self._create_central_area()
    
    def _create_menu(self):
        """Crée la barre de menu"""
        menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = menubar.addMenu("Fichier")
        
        new_action = QAction("Nouveau", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Ouvrir", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Sauvegarder", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Sauvegarder sous...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Quitter", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Menu Outils
        tools_menu = menubar.addMenu("Outils")
        
        datbox_action = QAction("Générer DATBOX", self)
        datbox_action.triggered.connect(self._on_generate_datbox)
        tools_menu.addAction(datbox_action)
        
        vars_action = QAction("Variables dynamiques", self)
        vars_action.triggered.connect(self._on_dynamic_vars)
        tools_menu.addAction(vars_action)
        
        # Menu Aide
        help_menu = menubar.addMenu("Aide")
        
        about_action = QAction("À propos", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Crée la barre d'outils"""
        toolbar = QToolBar("Actions")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        actions = [
            ("Nouveau", self.style().StandardPixmap.SP_FileIcon, self._on_new_project),
            ("Ouvrir", self.style().StandardPixmap.SP_DirOpenIcon, self._on_open_project),
            ("Sauvegarder", self.style().StandardPixmap.SP_DriveHDIcon, self._on_save_project),
            ("DATBOX", self.style().StandardPixmap.SP_FileDialogStart, self._on_generate_datbox),
        ]
        
        for text, icon, slot in actions:
            btn = QPushButton(text)
            btn.setIcon(self.style().standardIcon(icon))
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)
    
    def _create_tree_dock(self):
        """Crée le dock avec l'arbre du modèle"""
        dock = QDockWidget("Arbre du modèle", self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        
        self.tree_view = ModelTreeView(self.controller)
        dock.setWidget(self.tree_view.tree)
        dock.setMinimumWidth(400)
    
    def _create_central_area(self):
        """Crée la zone centrale avec splitter vertical"""
        # Splitter vertical (haut/bas)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(splitter)
        
        # Partie haute : Onglets de travail
        self._create_tabs()
        splitter.addWidget(self.tabs)
        
        # Partie basse : Widget de rendu
        self._create_render_widget()
        splitter.addWidget(self.render_widget)
        
        # Proportions : 70% tabs, 30% rendu
        splitter.setSizes([600, 400])
    
    def _create_tabs(self):
        """Crée les onglets de travail"""
        self.tabs = QTabWidget()
        
        # Créer chaque onglet
        self.material_tab = MaterialTab(self.controller)
        self.model_tab = ModelTab(self.controller)
        self.avatar_tab = AvatarTab(self.controller)
        self.empty_avatar_tab = EmptyAvatarTab(self.controller)
        self.loop_tab = LoopTab(self.controller)
        self.granulo_tab = GranuloTab(self.controller)
        self.dof_tab = DOFTab(self.controller)
        self.contact_tab = ContactTab(self.controller)
        self.visibility_tab = VisibilityTab(self.controller)
        self.postpro_tab = PostProTab(self.controller)
        
        # Ajouter aux onglets
        self.tabs.addTab(self.material_tab, "Matériau")
        self.tabs.addTab(self.model_tab, "Modèle")
        self.tabs.addTab(self.avatar_tab, "Avatar")
        self.tabs.addTab(self.empty_avatar_tab, "Avatar vide")
        self.tabs.addTab(self.loop_tab, "Boucles")
        self.tabs.addTab(self.granulo_tab, "Granulométrie")
        self.tabs.addTab(self.dof_tab, "DOF")
        self.tabs.addTab(self.contact_tab, "Contact")
        self.tabs.addTab(self.visibility_tab, "Visibilité")
        self.tabs.addTab(self.postpro_tab, "Post-Pro")
    
    def _create_render_widget(self):
        """Crée le widget de rendu (toujours visible en bas)"""
        self.render_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Groupe de visualisation
        viz_group = QGroupBox("🎨 Visualisation et Rendu")
        viz_layout = QHBoxLayout()
        
        # Bouton LMGC90
        lmgc_btn = QPushButton("📊 LMGC90 Visualisation")
        lmgc_btn.setToolTip("Visualise les avatars créés")
        lmgc_btn.setMinimumHeight(40)
        lmgc_btn.clicked.connect(self._on_lmgc_visualization)
        viz_layout.addWidget(lmgc_btn)
        
        # Bouton ParaView
        paraview_btn = QPushButton("🔬 Ouvrir ParaView")
        paraview_btn.setToolTip("Ouvre les résultats de simulation")
        paraview_btn.setMinimumHeight(40)
        paraview_btn.clicked.connect(self._on_paraview)
        viz_layout.addWidget(paraview_btn)
        
        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)
        """
        # Groupe génération
        gen_group = QGroupBox("⚙️ Génération")
        gen_layout = QHBoxLayout()
        
        # Bouton Générer Script Python
        script_btn = QPushButton("🐍 Générer Script Python")
        script_btn.setToolTip("Génère un script Python reproductible")
        script_btn.setMinimumHeight(40)
        script_btn.clicked.connect(self._on_generate_script)
        gen_layout.addWidget(script_btn)
        
        # Bouton Générer DATBOX (déplacé ici)
        datbox_btn = QPushButton("📦 Générer DATBOX")
        datbox_btn.setToolTip("Génère le fichier DATBOX pour LMGC90")
        datbox_btn.setMinimumHeight(40)
        datbox_btn.clicked.connect(self._on_generate_datbox)
        gen_layout.addWidget(datbox_btn)
        
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)
        
        # Informations
        info = QLabel(
            "<i>💡 LMGC90 : Affiche les avatars créés<br>"
            "💡 ParaView : Résultats après simulation<br>"
            "💡 Script Python : Génère un fichier .py reproductible<br>"
            "💡 DATBOX : Génère le fichier d'entrée pour le solveur</i>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 5px; font-size: 10px;")
        layout.addWidget(info)
        """
        self.render_widget.setLayout(layout)
        self.render_widget.setMinimumHeight(150)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.project_loaded.connect(self._refresh_all)
        self.project_saved.connect(self._refresh_all)
        
        self.material_tab.material_created.connect(self._refresh_all)
        self.model_tab.model_created.connect(self._refresh_all)
        self.avatar_tab.avatar_created.connect(self._refresh_all)
        self.empty_avatar_tab.avatar_created.connect(self._refresh_all)
        self.loop_tab.loop_generated.connect(self._refresh_all)
        self.granulo_tab.granulo_generated.connect(self._refresh_all)
        self.dof_tab.operation_applied.connect(self._refresh_all)
        self.contact_tab.law_created.connect(self._refresh_all)
        
    
    # ========== SLOTS MENU ==========
    
    def _on_new_project(self):
        """Crée un nouveau projet"""
        from PyQt6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(
            self, "Nouveau projet", 
            "Nom du projet :", 
            text="Mon_Projet"
        )
        
        if ok and name.strip():
            name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name.strip())
            self.controller.new_project(name)
            self.setWindowTitle(f"LMGC90_GUI v0.2.5 - {name}")
            self._refresh_all()
            self.statusBar().showMessage("Nouveau projet créé", 3000)
    
    def _on_open_project(self):
        """Ouvre un projet existant"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir projet", "",
            "Projet LMGC90 (*.lmgc90)"
        )
        
        if filepath:
            try:
                self.controller.load_project(Path(filepath))
                self.setWindowTitle(f"LMGC90_GUI v0.2.5 - {self.controller.state.name}")
                self.project_loaded.emit()
                if hasattr(self.controller.state, 'load_warnings'):
                    warnings = '\n'.join(self.controller.state.load_warnings)
                    QMessageBox.warning(self, "Avertissements", 
                        f"Certains éléments n'ont pas pu être régénérés :\n\n{warnings}")
                self.statusBar().showMessage(f"Projet chargé", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de charger :\n{e}")
    
    def _on_save_project(self):
        """Sauvegarde le projet"""
        if not self.controller.project_path:
            return self._on_save_project_as()
        
        try:
            self.controller.save_project()
            self.project_saved.emit()
            self.statusBar().showMessage("Projet sauvegardé", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Sauvegarde échouée :\n{e}")
    
    def _on_save_project_as(self):
        """Sauvegarde sous..."""
        dirpath = QFileDialog.getExistingDirectory(self, "Choisir le dossier")
        
        if dirpath:
            filename = f"{self.controller.state.name}.lmgc90"
            filepath = Path(dirpath) / filename
            
            try:
                self.controller.save_project(filepath)
                self.project_saved.emit()
                self.statusBar().showMessage(f"Sauvegardé", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Sauvegarde échouée :\n{e}")
    
    def _on_generate_datbox(self):
        """Génère le fichier DATBOX"""
        if not self.controller.project_path:
            QMessageBox.warning(self, "Attention", "Enregistrez d'abord le projet")
            return self._on_save_project_as()
        
        output_path = self.controller.project_path.parent / "DATBOX"
        
        try:
            self.controller.generate_datbox(output_path)
            QMessageBox.information(self, "Succès", f"DATBOX généré !\n{output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _on_dynamic_vars(self):
        """Ouvre le dialogue des variables dynamiques"""
        from .dialogs import DynamicVarsDialog
        
        dialog = DynamicVarsDialog(self.controller.state.dynamic_vars, self)
        if dialog.exec():
            self.controller.state.dynamic_vars = dialog.get_vars()
            self.statusBar().showMessage(
                f"{len(self.controller.state.dynamic_vars)} variables définies", 3000
            )
    
    def _on_about(self):
        """Affiche À propos"""
        QMessageBox.information(
            self, "À propos",
            "LMGC90_GUI v0.2.5\n\n"
            "Architecture MVC refactorisée\n"
            "par Zerourou B.\n\n"
            "© 2025 - Open Source"
        )
    
    # ========== VISUALISATION ET GÉNÉRATION ==========
    
    def _on_generate_script(self):
        """Génère un script Python reproductible"""
        if not self.controller.project_path:
            QMessageBox.warning(self, "Attention", "Enregistrez d'abord le projet")
            return self._on_save_project_as()
        
        output_path = self.controller.project_path.parent / f"{self.controller.state.name}.py"
        
        try:
            self.statusBar().showMessage("Génération du script...", 2000)
            QApplication.processEvents()
            
            # Importer le générateur de script
            from ..utils.script_generator import ScriptGenerator
            
            # Générer le script
            generator = ScriptGenerator(self.controller)
            generator.generate(output_path)
            
            # Succès
            reply = QMessageBox.question(
                self, "Script généré !",
                f"Script Python généré avec succès !\n\n{output_path}\n\n"
                "Voulez-vous ouvrir le fichier ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import subprocess
                import sys
                if sys.platform == 'win32':
                    subprocess.Popen(['notepad', str(output_path)])
                else:
                    subprocess.Popen(['xdg-open', str(output_path)])
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _on_lmgc_visualization(self):
        """Lance la visualisation LMGC90"""
        try:
            from pylmgc90 import pre
            
            if not self.controller._pylmgc_bodies:
                QMessageBox.warning(self, "Attention", "Aucun avatar à visualiser")
                return
            
            self.statusBar().showMessage("Visualisation...", 2000)
            QApplication.processEvents()
            
            pre.visuAvatars(self.controller._bodies_container)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Visualisation échouée :\n{e}")
    
    def _on_paraview(self):
        """Ouvre ParaView"""
        import subprocess
        import shutil
        import glob
        
        if not self.controller.project_path:
            QMessageBox.warning(self, "Attention", "Enregistrez d'abord le projet")
            return
        
        try:
            pvd_file = self.controller.project_path.parent / "DISPLAY" / "rigids.pvd"
            
            if not pvd_file.exists():
                QMessageBox.warning(
                    self, "Fichier introuvable",
                    f"rigids.pvd n'existe pas.\n"
                    f"Exécutez d'abord la simulation LMGC90."
                )
                return
            
            # Chercher ParaView
            paraview_exe = shutil.which('paraview')
            if not paraview_exe:
                for pattern in [r"C:\Program Files\ParaView*\bin\paraview.exe"]:
                    matches = glob.glob(pattern)
                    if matches:
                        paraview_exe = matches[0]
                        break
            
            if not paraview_exe:
                QMessageBox.critical(self, "ParaView introuvable", 
                    "Installez ParaView depuis https://www.paraview.org/")
                return
            
            subprocess.Popen([paraview_exe, str(pvd_file)])
            self.statusBar().showMessage("ParaView lancé", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur ParaView :\n{e}")
    
    # ========== RAFRAÎCHISSEMENT ==========
    
    def _refresh_all(self):
        """Rafraîchit toute l'interface"""
        self.tree_view.refresh()
        
        for tab in [self.material_tab, self.model_tab, self.avatar_tab,
                   self.empty_avatar_tab, self.loop_tab, self.granulo_tab,
                   self.dof_tab, self.contact_tab, self.visibility_tab,
                   self.postpro_tab]:
            if hasattr(tab, 'refresh'):
                tab.refresh()