"""
Fenêtre principale de l'application.
Interface entre l'utilisateur et le contrôleur.
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QPushButton, QTabWidget, QMessageBox,
    QFileDialog, QApplication, QDialog, QTextEdit, QVBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QProcess, QProcessEnvironment
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from pathlib import Path

from ..controllers.project_controller import ProjectController
from ..core.validators import ValidationError
from .tabs import (
    MaterialTab, ModelTab, AvatarTab, EmptyAvatarTab, AvatarLibraryTab, LoopTab,
    GranuloTab, DOFTab, ContactTab, VisibilityTab, PostProTab, ComputeTab, ViewerTab
)

from ..core.models import UnitSystem
from ..core.app_logger import get_logger, get_log_path, get_log_dir, get_recent_logs
_log = get_logger('main_window')
from ..gui.dialogs.fast_granulo_dialg import GranuloFastDialog
from ..gui.dialogs.convert_dialog import ConvertDialog

from ..views.main_window_parts import (
    CommandPaletteController,
    MainWindowTabsMixin,
    MainWindowTreeMixin,
    MainWindowLayoutMixin,
)

import threading


class MainWindow(
    QMainWindow, MainWindowTabsMixin, MainWindowTreeMixin, MainWindowLayoutMixin
):
    """Fenêtre principale de l'application"""
    
    # Signaux
    project_loaded = pyqtSignal()
    project_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        # Contrôleur
        self.controller = ProjectController()
        if not hasattr(self.controller.state, 'preferences'):
            from ..core.models import ProjectPreferences
            self.controller.state.preferences = ProjectPreferences()

        # Suivi du sous-processus d'exécution de script (voir _on_run_script)
        self._script_process = None
        self._script_log_dialog = None
        
        # Configuration fenêtre
        self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {self.controller.state.name}")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("lmgc90_gui.ico"))
        
        # Interface
        self._setup_ui()
        self._connect_signals()
        self._update_recent_menu()
        
        # État initial
        self.statusBar().showMessage("Prêt", 3000)

        self._refresh_all()
    
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

        self._command_palette = CommandPaletteController(self)
        self._command_palette.setup_shortcut()
    
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

        self.recent_menu = file_menu.addMenu("📂 Projets récents")

        file_menu.addSeparator()
        
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
    
        # Menu Assistants
        assistants_menu = menubar.addMenu("🧙 Assistants...")

        project_wizard_action = QAction("🧙 Assistant de Projet...", self)
        project_wizard_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        project_wizard_action.triggered.connect(self._on_project_wizard)
        assistants_menu.addAction(project_wizard_action)

        assistants_menu.addSeparator()

        granulo_wizard_action = QAction("🎲 Assistant de granulométrie...", self)
        granulo_wizard_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
        granulo_wizard_action.triggered.connect(self._on_granulo_wizard)
        assistants_menu.addAction(granulo_wizard_action)

        fast_granulo_action = QAction("⚡ Génération granulométrie numpy... (bêta)", self)
        fast_granulo_action.triggered.connect(self._open_fast_granulo)
        assistants_menu.addAction(fast_granulo_action)

        assistants_menu.addSeparator()

        deformable_wizard_action = QAction("🔧 Assistant de déformable...", self)
        deformable_wizard_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        deformable_wizard_action.triggered.connect(self._on_deformable_wizard)
        assistants_menu.addAction(deformable_wizard_action)

        assistants_menu.addSeparator()

        masonry_wizard_action = QAction("🧱 Assistant de maçonnerie...", self)
        masonry_wizard_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        masonry_wizard_action.triggered.connect(self._on_masonry_wizard)
        assistants_menu.addAction(masonry_wizard_action)

        assistants_menu.addSeparator()

        factory_wizard_action = QAction("🏭 Assistant de Factory...", self)
        factory_wizard_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        factory_wizard_action.triggered.connect(self._on_factory_wizard)
        assistants_menu.addAction(factory_wizard_action)


        # Menu Outils
        tools_menu = menubar.addMenu("Outils")

        # Menu Exemples
        examples_menu = menubar.addMenu("📚 Exemples")

        browse_examples_action = QAction("📂 Parcourir les exemples...", self)
        browse_examples_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        browse_examples_action.triggered.connect(self._on_browse_examples)
        examples_menu.addAction(browse_examples_action)

        datbox_action = QAction("Générer DATBOX", self)
        datbox_action.triggered.connect(self._on_generate_datbox)
        tools_menu.addAction(datbox_action)

        script_action = QAction("Générer Script Python", self)
        script_action.triggered.connect(self._on_generate_script)
        tools_menu.addAction(script_action)
        
        tools_menu.addSeparator()

        convert_action = QAction("🔄 Convertir script pylmgc90", self)
        convert_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        convert_action.triggered.connect(self._on_convert_script)
        tools_menu.addAction(convert_action)
        
        vars_action = QAction("Variables dynamiques", self)
        vars_action.setShortcut(QKeySequence("Ctrl+V"))
        vars_action.triggered.connect(self._on_dynamic_vars)
        tools_menu.addAction(vars_action)

        tools_menu.addSeparator()

        #Préférences
        prefs_action = QAction("⚙️ Préférences...", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))  # Raccourci
        prefs_action.triggered.connect(self._on_preferences)
        tools_menu.addAction(prefs_action)

        
        # Menu calcul
        compute_menu = menubar.addMenu("Calcul")
        

        setup_action = QAction("⚙️ Paramètres de Calcul", self)
        setup_action.setShortcut(QKeySequence("Ctrl+F5"))
        setup_action.triggered.connect(self._on_compute_setup)
        compute_menu.addAction(setup_action)

        run_action = QAction("▶️ Lancer le Calcul", self)
        run_action.setShortcut(QKeySequence("F5"))
        run_action.triggered.connect(self._on_run_compute)
        compute_menu.addAction(run_action)

        compute_menu.addSeparator()
        
        gen_script_action = QAction("📄 Générer Script Calcul", self)
        gen_script_action.triggered.connect(self._on_generate_compute_script)
        compute_menu.addAction(gen_script_action)

        logs_action = QAction("📄 Voir Logs LMGC90", self)
        logs_action.setShortcut("F6")
        logs_action.triggered.connect(self._on_show_logs)
        compute_menu.addAction(logs_action)

        app_logs_action = QAction("📋 Journal de l'application", self)
        app_logs_action.setShortcut("F7")
        app_logs_action.triggered.connect(self._on_show_app_log)
        compute_menu.addAction(app_logs_action)
        
        # menu tabs
        tabs_menu = menubar.addMenu("📑 Onglets")
        # Sous-menu pour ouvrir des onglets
        open_submenu = tabs_menu.addMenu("➕ Ouvrir")
        
        all_tab_actions = [
            ('material', '🧱 Matériau'),
            ('model', '⚙️ Modèle'),
            ('avatar', '🎯 Avatar'),
            ('empty_avatar', '⭕ Avatar vide'),
            ('library', '📚 Bibliothèque'),
            ('loop', '🔁 Boucles'),
            ('granulo', '🎲 Granulométrie'),
            ('dof', '🔒 DOF'),
            ('contact', '⚡ Contact'),
            ('visibility', '👁️ Visibilité'),
            ('postpro', '📊 Post-Pro'),
            ('compute', '⚙️ Calcul'),
            ('viewer', '🎨 Visualisation 3D')
        ]
        
        for tab_id, tab_name in all_tab_actions:
            action = open_submenu.addAction(tab_name)

            action.setShortcut(QKeySequence(f"Ctrl+{len(open_submenu.actions())}"))   # sans 10, 11 et 12

            action.triggered.connect(lambda checked, tid=tab_id: self._add_tab(tid))
        
        tabs_menu.addSeparator()
        
        close_others_action = tabs_menu.addAction("❌ Fermer les autres")
        close_others_action.triggered.connect(self._close_other_tabs)
        
        close_all_action = tabs_menu.addAction("🗑️ Fermer tous (sauf essentiels)")
        close_all_action.triggered.connect(self._close_all_tabs)
        
        tabs_menu.addSeparator()
        
        defaults_action = tabs_menu.addAction("🔄 Onglets par défaut")
        defaults_action.setShortcut(QKeySequence("Ctrl+Alt+D"))
        defaults_action.triggered.connect(self._reopen_default_tabs)

        # Menu Aide
        help_menu = menubar.addMenu("Aide")
        aide_action = QAction("Aide en ligne ", self)
        about_action = QAction("À propos", self)
        about_action.triggered.connect(self._on_about)
        aide_action.triggered.connect(self._on_help)
        help_menu.addAction(about_action)
        help_menu.addAction(aide_action)
    
    def _create_toolbar(self):
        """Crée la barre d'outils"""
        toolbar = QToolBar("Actions")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        actions = [
            ("Nouveau", self.style().StandardPixmap.SP_FileIcon, self._on_new_project),
            ("Ouvrir", self.style().StandardPixmap.SP_DirOpenIcon, self._on_open_project),
            ("Sauvegarder", self.style().StandardPixmap.SP_DriveHDIcon, self._on_save_project),
            ("DATBOX", self.style().StandardPixmap.SP_FileDialogStart, self._on_generate_datbox),
            ("Script Python", self.style().StandardPixmap.SP_FileDialogDetailedView, self._on_generate_script),
            ("Exécuter Script", self.style().StandardPixmap.SP_MediaPlay, self._on_run_script),
            ("Charger Factory", self.style().StandardPixmap.SP_FileDialogListView, self._on_load_factory_avatars),
   
        ]
        
        for text, icon, slot in actions:
            btn = QPushButton(text)
            btn.setIcon(self.style().standardIcon(icon))
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)
    
    def _create_tabs(self):
        """Crée les onglets de travail"""
        self.tabs = QTabWidget()

        #fermeture des tabs 
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        
        # Créer chaque onglet
        self.material_tab = MaterialTab(self.controller)
        self.model_tab = ModelTab(self.controller)
        self.avatar_tab = AvatarTab(self.controller)
        self.empty_avatar_tab = EmptyAvatarTab(self.controller)
        self.avatar_library_tab = AvatarLibraryTab(self.controller)
        self.loop_tab = LoopTab(self.controller)
        self.granulo_tab = GranuloTab(self.controller)
        self.dof_tab = DOFTab(self.controller)
        self.contact_tab = ContactTab(self.controller)
        self.visibility_tab = VisibilityTab(self.controller)
        self.postpro_tab = PostProTab(self.controller)
        self.compute_tab = ComputeTab(self.controller)
        self.viewer_tab = ViewerTab(self.controller)
        
    # Ajouter aux onglets
    # Dictionnaire pour gérer les onglets
        self.all_tabs = {
            'material': ('Matériau', self.material_tab, '🧱'),
            'model': ('Modèle', self.model_tab, '⚙️'),
            'avatar': ('Avatar', self.avatar_tab, '🎯'),
            'empty_avatar': ('Avatar vide', self.empty_avatar_tab, '⭕'),
            'library': ('Bibliothèque', self.avatar_library_tab, '📚'),
            'loop': ('Boucles', self.loop_tab, '🔁'),
            'granulo': ('Granulométrie', self.granulo_tab, '🎲'),
            'dof': ('DOF', self.dof_tab, '🔒'),
            'contact': ('Contact', self.contact_tab, '⚡'),
            'visibility': ('Visibilité', self.visibility_tab, '👁️'),
            'postpro': ('Post-Pro', self.postpro_tab, '📊'),
            'compute': ('Calcul', self.compute_tab, '⚙️'),
            'viewer': ('Visualisation 3D', self.viewer_tab, '🎨')
        }
        
        # Onglets ouverts par défaut
        default_tabs = ['material', 'model', 'avatar']
        
        for tab_id in default_tabs:
            self._add_tab(tab_id)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.project_loaded.connect(self._refresh_all)
        self.project_saved.connect(self._refresh_all)
        #matériaux
        self.material_tab.material_created.connect(self._refresh_all)
        self.material_tab.material_updated.connect(self._refresh_all)
        self.material_tab.material_deleted.connect(self._refresh_all)
        #modèles
        self.model_tab.model_created.connect(self._refresh_all)
        self.model_tab.model_updated.connect(self._refresh_all)
        self.model_tab.model_deleted.connect(self._refresh_all)
        self.model_tab.dimension_changed.connect( self.avatar_tab._update_avatar_types)

        #avatars
        self.avatar_tab.avatar_created.connect(self._refresh_all)
        self.avatar_tab.avatar_updated.connect(self._refresh_all)
        self.avatar_tab.avatar_deleted.connect(self._refresh_all)
        self.empty_avatar_tab.avatar_created.connect(self._refresh_all)
        self.empty_avatar_tab.avatar_updated.connect(self._refresh_all)
        self.empty_avatar_tab.avatar_deleted.connect(self._refresh_all)
        
        #loops
        self.loop_tab.loop_generated.connect(self._refresh_all)
        self.loop_tab.loop_deleted.connect(self._refresh_all)
        self.loop_tab.loop_updated.connect(self._refresh_all)
        #granulo
        self.granulo_tab.granulo_generated.connect(self._refresh_all)
        self.granulo_tab.granulo_deleted.connect(self._refresh_all)
        #dof
        self.dof_tab.operation_applied.connect(self._refresh_all)   
        self.dof_tab.operation_deleted.connect(self._refresh_all)
        # rafraîchir viewer
        self.dof_tab.operation_applied.connect(self.viewer_tab.refresh)
        #contact
        self.contact_tab.law_created.connect(self._refresh_all)
        self.contact_tab.law_updated.connect(self._refresh_all)
        self.contact_tab.law_deleted.connect(self._refresh_all)
        #visibility
        self.visibility_tab.rule_created.connect(self._refresh_all)
        self.visibility_tab.rule_updated.connect(self._refresh_all)
        self.visibility_tab.rule_deleted.connect(self._refresh_all)
        #postpro
        self.postpro_tab.command_added.connect(self._refresh_all)
        self.postpro_tab.command_deleted.connect(self._refresh_all)
        #viewer
        # Rafraîchir le viewer quand avatars changent
        #self.avatar_tab.avatar_created.connect(self.viewer_tab.refresh)
        #self.avatar_tab.avatar_updated.connect(self.viewer_tab.refresh)
        #self.avatar_tab.avatar_deleted.connect(self.viewer_tab.refresh)
        #self.loop_tab.loop_generated.connect(self.viewer_tab.refresh)
        #self.granulo_tab.granulo_generated.connect(self.viewer_tab.refresh)
        # librairie d'avatars 
        self.controller.state_changed.connect(self.avatar_tab.refresh)
        self.controller.state_changed.connect(self.material_tab.refresh)
        self.controller.state_changed.connect(self.model_tab.refresh)
        self.controller.state_changed.connect(self.avatar_library_tab.refresh)
        self.controller.state_changed.connect(self._refresh_all)
        self.model_tab.dimension_changed.connect( self.avatar_library_tab.refresh)


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
            self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {name}")
            self._refresh_all()
            self.statusBar().showMessage("Nouveau projet créé", 3000)
        
    
    def _on_open_project(self):
        """Ouvre un projet existant"""
        start_dir = ""
        if self.controller.state.preferences.default_project_path:
            start_dir = str(self.controller.state.preferences.default_project_path)
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir projet", "",
            "Projet LMGC90 (*.lmgc90)"
        )
        
        if filepath:
            try:
                self.controller.load_project(Path(filepath))
                self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {self.controller.state.name}")
                self.project_loaded.emit()
                self._add_to_recent(Path(filepath))
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
        # Utiliser le chemin par défaut si défini
        start_dir = ""
        if self.controller.state.preferences.default_project_path:
            start_dir = str(self.controller.state.preferences.default_project_path)
        
        dirpath = QFileDialog.getExistingDirectory(self, "Choisir le dossier", start_dir)
        
        if dirpath:
            filename = f"{self.controller.state.name}.lmgc90"
            filepath = Path(dirpath) / filename
            
            try:
                self.controller.save_project(filepath)
                self.project_saved.emit()
                self.statusBar().showMessage(f"Sauvegardé", 5000)
                
                #Ajouter à l'historique
                self._add_to_recent(filepath)
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Sauvegarde échouée :\n{e}")
    
    #====== Génération DATBOX ==================
    
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

    def _update_recent_menu(self):
        """Met à jour le menu des projets récents."""
        if not hasattr(self, "recent_menu"):
            return

        self.recent_menu.clear()
        preferences = getattr(self.controller.state, "preferences", None)
        recent_projects = getattr(preferences, "recent_projects", [])

        if not recent_projects:
            empty_action = self.recent_menu.addAction("(Aucun projet récent)")
            empty_action.setEnabled(False)
            return

        for project_path in recent_projects[:10]:
            project_path = Path(project_path)
            if project_path.exists():
                action = self.recent_menu.addAction(f"📄 {project_path.name}")
                action.triggered.connect(
                    lambda checked=False, path=project_path: self._open_recent_project(path)
                )
            else:
                action = self.recent_menu.addAction(
                    f"❌ {project_path.name} (introuvable)"
                )
                action.setEnabled(False)

        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("🗑️ Effacer l'historique")
        clear_action.triggered.connect(self._clear_recent_projects)
    
 

    # ======Tabs======================

    # =======Menu Outils =============
    def _on_browse_examples(self):
            """Ouvre la bibliothèque d'exemples et charge celui choisi."""
            from ..gui.dialogs.examples_dialog import ExamplesDialog
            from ..examples import get_example

            dlg = ExamplesDialog(self)
            if dlg.exec() != ExamplesDialog.DialogCode.Accepted:
                return

            example = get_example(dlg.selected_example_id)
            if example is None:
                return

            try:
                self.controller.new_project(example.title)
                example.builder(self.controller)
                self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {self.controller.state.name}")
                self._refresh_all()
                self.statusBar().showMessage(
                    f"✅ Exemple « {example.title} » chargé", 5000
                )
            except Exception as e:
                import traceback
                QMessageBox.critical(
                    self, "Erreur",
                    f"Échec du chargement de l'exemple :\n{e}\n\n{traceback.format_exc()}"
                )

    def _on_dynamic_vars(self):
        """Ouvre le dialogue des variables dynamiques"""
        from .dialogs import DynamicVarsDialog
        
        dialog = DynamicVarsDialog(self.controller.state.dynamic_vars, self.controller, self)
        if dialog.exec():
            self.controller.state.dynamic_vars = dialog.get_vars()
            self.statusBar().showMessage(
                f"{len(self.controller.state.dynamic_vars)} variables définies", 3000
            )
    
    def _on_about(self):
        """Affiche À propos"""
        QMessageBox.information(
            self, "À propos",
            "LMGC90_GUI v0.4.7\n"
            "UI pour LMGC90\n"
            "par Zerourou B.\n"
            "bachir.zerourou@yahoo.fr\n"
            "© 2026 - Open Source"
        )

    def _on_help(self) :
        import webbrowser
        webbrowser.open("https://github.com/bzerourou/LMG90_GUI_MVC/blob/main/docs/overview.md")

    def _on_preferences(self):
        """Ouvre le dialogue de préférences"""
        from .dialogs import PreferencesDialog
       
        if not hasattr(self.controller.state, 'preferences'):
            from ..core.models import ProjectPreferences
            self.controller.state.preferences = ProjectPreferences()
        dialog = PreferencesDialog(
            preferences=self.controller.state.preferences,
            parent=self
        )
        
        if dialog.exec():
            # Récupérer les nouvelles préférences
            new_prefs = dialog.get_preferences()
            self.controller.state.preferences = new_prefs
            
            # Appliquer les changements
            self._apply_preferences()
            # rafraichir tout
            self._refresh_all()
            
            QMessageBox.information(
                self, "Préférences",
                "✅ Préférences sauvegardées.\n\n"
                "Certains changements prendront effet au prochain démarrage."
        )
            self._update_recent_menu()

    def _apply_preferences(self):
        """Applique les préférences"""
        if not hasattr(self.controller.state, 'preferences'):
            return
        
        prefs = self.controller.state.preferences
        
        # Mettre à jour les labels d'unités dans l'interface
        unit_labels = prefs.get_unit_labels()
        
        # Mettre à jour la barre de statut
        unit_system_name = "SI" if prefs.unit_system == UnitSystem.SI else "CGS"
        self.statusBar().showMessage(f"Système d'unités : {unit_system_name}", 5000)

    def _open_recent_project(self, filepath: Path):
        """Ouvre un projet récent."""
        try:
            self.controller.load_project(filepath)
            self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {self.controller.state.name}")
            self.project_loaded.emit()
            self.statusBar().showMessage(f"Projet chargé", 5000)
            
            # Mettre à jour l'historique
            self._add_to_recent(filepath)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger :\n{e}")

    def _add_to_recent(self, filepath: Path):
        """Ajoute un projet à l'historique"""
        prefs = self.controller.state.preferences
        
        # Retirer si déjà présent
        if filepath in prefs.recent_projects:
            prefs.recent_projects.remove(filepath)
        
        # Ajouter en tête
        prefs.recent_projects.insert(0, filepath)
        
        # Limiter la taille
        max_recent = prefs.max_recent_projects
        prefs.recent_projects = prefs.recent_projects[:max_recent]
        
        # Mettre à jour le menu
        self._update_recent_menu()

    def _clear_recent_projects(self):
        """Efface l'historique des projets récents"""
        reply = QMessageBox.question(
            self, "Confirmer",
            "Effacer l'historique des projets récents ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.state.preferences.recent_projects.clear()
            self._update_recent_menu()

    # ======== Plattes des commandes =================================== 

    def _on_command_entered(self, text: str):
        """Interprète une commande tapée dans la CommandBar."""
        parts = text.split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]

        try:
            handler = self._COMMANDS.get(cmd)
            if handler is None:
                self.command_bar.set_status(f"Commande inconnue : '{cmd}' (essayez 'help')", ok=False)
                return
            handler(self, args)
            self.command_bar.set_status(f"✓ {text}", ok=True)
        except Exception as e:
            self.command_bar.set_status(f"Erreur : {e}", ok=False)

        self.statusBar().showMessage(f"> {text}", 3000)

    # ── Table de dispatch des commandes ──────────────────────────────────────
    def _cmd_help(self, args):
        QMessageBox.information(self, "Commandes disponibles",
            "tab <id>              — ouvre un onglet (avatar, material, model, loop, "
            "granulo, dof, contact, visibility, postpro, compute, viewer, empty_avatar, library)\n"
            "close <id>            — ferme un onglet\n"
            "dim <2|3>             — change la dimension du projet\n"
            "viewer color <mode>   — mode couleur du viewer (lmgc90|type|material|origin)\n"
            "viewer refresh        — rafraîchit la scène 3D\n"
            "viewer edges <on|off> — affiche/masque les arêtes\n"
            "units <si|cgs>        — change le système d'unités\n"
            "save                  — sauvegarde le projet\n"
            "new <nom>             — nouveau projet\n"
            "wizard project       — assistant de projet\n"
            "wizard granulo       — assistant de granulométrie\n"
            "wizard fast-granulo  — générateur granulométrique rapide\n"
            "datbox               — génère DATBOX\n"
            "script               — génère le script Python\n"
            "compute setup        — ouvre les paramètres de calcul\n"
            "logs app|lmgc90      — affiche les journaux\n"
            "tabs default         — rouvre les onglets par défaut\n"
            "menu <nom>           — ouvre un menu principal\n"
        )

    def _cmd_tab(self, args):
        if not args:
            raise ValueError("usage: tab <id>")
        self._add_tab(args[0])

    def _cmd_close(self, args):
        if not args or args[0] not in self.all_tabs:
            raise ValueError("usage: close <id>")
        widget = self.all_tabs[args[0]][1]
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) is widget:
                self._on_tab_close_requested(i)
                return

    def _cmd_dim(self, args):
        if not args or args[0] not in ("2", "3"):
            raise ValueError("usage: dim <2|3>")
        dim = int(args[0])
        ok, reasons = self.controller.can_change_dimension(dim)
        self.controller.set_dimension(dim, force=not ok)
        self._refresh_all()

    def _cmd_viewer(self, args):
        if not args:
            raise ValueError("usage: viewer <color|refresh|edges> ...")
        sub = args[0]
        v = self.viewer_tab.viewer
        if sub == "color" and len(args) > 1:
            modes = {"lmgc90": 0, "type": 1, "material": 2, "origin": 3}
            idx = modes.get(args[1].lower())
            if idx is None:
                raise ValueError("mode: lmgc90|type|material|origin")
            v._color_combo.setCurrentIndex(idx)
        elif sub == "refresh":
            self.viewer_tab._do_refresh()
        elif sub == "edges" and len(args) > 1:
            v._edges_check.setChecked(args[1].lower() in ("on", "1", "true"))
        else:
            raise ValueError("sous-commande viewer inconnue")

    def _cmd_units(self, args):
        from ..core.models import UnitSystem
        if not args or args[0].lower() not in ("si", "cgs"):
            raise ValueError("usage: units <si|cgs>")
        self.controller.state.preferences.unit_system = (
            UnitSystem.SI if args[0].lower() == "si" else UnitSystem.CGS
        )
        self._refresh_all()

    def _cmd_save(self, args):
        self._on_save_project()

    def _cmd_new(self, args):
        name = " ".join(args).strip() or "Nouveau_Projet"
        name = "".join(
            char if char.isalnum() or char in "_-" else "_"
            for char in name
        )
        self.controller.new_project(name)
        from ..core.models import ProjectPreferences
        self.controller.state.preferences = ProjectPreferences()
        self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {name}")
        self._refresh_all()
        self._update_recent_menu()
        self.statusBar().showMessage("Nouveau projet créé", 3000)

    def _cmd_wizard(self, args):
        if len(args) != 1:
            raise ValueError("usage: wizard <project|granulo|fast-granulo>")
        actions = {
            "project": self._on_project_wizard,
            "granulo": self._on_granulo_wizard,
            "fast-granulo": self._open_fast_granulo,
        }
        action = actions.get(args[0].lower())
        if action is None:
            raise ValueError("assistant inconnu: project|granulo|fast-granulo")
        action()

    def _cmd_datbox(self, args):
        if args:
            raise ValueError("usage: datbox")
        self._on_generate_datbox()

    def _cmd_script(self, args):
        if args:
            raise ValueError("usage: script")
        self._on_generate_script()

    def _cmd_compute(self, args):
        if args != ["setup"]:
            raise ValueError("usage: compute setup")
        self._on_compute_setup()

    def _cmd_logs(self, args):
        if len(args) != 1 or args[0].lower() not in ("app", "lmgc90"):
            raise ValueError("usage: logs <app|lmgc90>")
        if args[0].lower() == "app":
            self._on_show_app_log()
        else:
            self._on_show_logs()

    def _cmd_tabs(self, args):
        if args != ["default"]:
            raise ValueError("usage: tabs default")
        self._reopen_default_tabs()

    def _cmd_menu(self, args):
        """Ouvre un menu principal depuis la barre de commande."""
        menu_names = {
            "fichier": "Fichier",
            "assistants": "Assistants",
            "outils": "Outils",
            "exemples": "Exemples",
            "calcul": "Calcul",
            "onglets": "Onglets",
            "aide": "Aide",
        }
        if len(args) != 1 or args[0].lower() not in menu_names:
            raise ValueError(
                "usage: menu <fichier|assistants|outils|calcul|onglets|aide>"
            )

        requested = menu_names[args[0].lower()]
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu is not None and requested.lower() in menu.title().lower():
                menu_pos = self.menuBar().actionGeometry(action).bottomLeft()
                menu.popup(self.menuBar().mapToGlobal(menu_pos))
                return
        raise RuntimeError(f"menu introuvable: {requested}")

    def _refresh_command_suggestions(self):
        """Construit la liste d'autocomplétion à partir des commandes + contexte projet."""
        suggestions = []
        for name in self._COMMANDS:
            suggestions.append(name)

        # tab <id> — un item complet par onglet, plus pratique à taper
        for tab_id in self.all_tabs:
            suggestions.append(f"tab {tab_id}")
            suggestions.append(f"close {tab_id}")

        suggestions += [
            "dim 2", "dim 3",
            "viewer color lmgc90", "viewer color type",
            "viewer color material", "viewer color origin",
            "viewer refresh", "viewer edges on", "viewer edges off",
            "units si", "units cgs",
            "new",
            "save", 
            "help",
            "wizard project", "wizard granulo", "wizard fast-granulo",
            "datbox", "script", "compute setup", "logs app", "logs lmgc90",
            "tabs default",
            "menu fichier", "menu assistants", "menu outils", "menu calcul",
            "menu onglets", "menu aide",
        ]
        self.command_bar.set_suggestions(suggestions)

    _COMMANDS = {
        "help": _cmd_help,
        "tab": _cmd_tab,
        "close": _cmd_close,
        "dim": _cmd_dim,
        "viewer": _cmd_viewer,
        "units": _cmd_units,
        "save": _cmd_save,
        "new": _cmd_new,
        "wizard": _cmd_wizard,
        "datbox": _cmd_datbox,
        "script": _cmd_script,
        "compute": _cmd_compute,
        "logs": _cmd_logs,
        "tabs": _cmd_tabs,
        "menu": _cmd_menu
}
    
    # ========Wizard ===================================

    def _on_project_wizard(self):
        """Lance l'assistant de configuration"""
        from ..gui.dialogs.setup_wizard import ProjectSetupWizard
        
        wizard = ProjectSetupWizard(self.controller, self)
        if wizard.exec():
            self.setWindowTitle(f"LMGC90_GUI v0.4.7 - {self.controller.state.name}")
            self._refresh_all()
            self.statusBar().showMessage("✅ Projet créé via l'assistant", 5000)

    def _on_granulo_wizard(self) : 
        """Lance l'assistant granulométrique"""
        from ..gui.dialogs.granulo_wizard import GranuloWizard
        
        wizard = GranuloWizard(self.controller, self)
        if wizard.exec():
            self._refresh_all()
            self.statusBar().showMessage("✅ Distribution granulométrique générée", 5000)

    def _on_deformable_wizard(self) : 
        """Lance l'assistant granulométrique"""
        from ..gui.dialogs.mesh_wiz_def import MeshWizard
        
        wizard = MeshWizard(self.controller, self)
        if wizard.exec():
            self._refresh_all()
            self.statusBar().showMessage("✅ Distribution granulométrique générée", 5000)

    def _open_fast_granulo(self):
        dlg = GranuloFastDialog(self.controller, parent=self)
        dlg.granulo_generated.connect(self._refresh_all)
        dlg.exec()

    def _on_masonry_wizard(self) :
        """Lance l'assistant de maçonnerie"""
        from ..gui.dialogs.masonery_wizard import MasonryWizard
        
        wizard = MasonryWizard(self.controller, self)
        if wizard.exec():
            self._refresh_all()
            self.statusBar().showMessage("✅ Maçonnerie générée", 5000)

    def _on_factory_wizard(self) :
        """Lance l'assistant de Factory"""
        from ..gui.dialogs.factory_wizard import FactoryWizard
        from ..core.particle_factory import ParticleFactory
        
        wizard = FactoryWizard(self.controller, self)
        if wizard.exec() and wizard.result_config:
            # Persister la factory dans ProjectState
            if not hasattr(self.controller.state, 'factories'):
                self.controller.state.factories = []
            engine = wizard.engine
            nb_existing = len(self.controller.state.avatars)
            engine.reset_body_counter(nb_existing + 1)
            for cfg in engine.configs:
                engine._assign_body_indices(cfg)
            self.controller.state.factories = engine.to_list_of_dicts()
            self._refresh_all()
            self.statusBar().showMessage("✅ Factory générée", 5000)
        
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

    def _on_run_script(self):
        """
        Exécute le script Python généré (<projet>.py) dans un sous-processus.

        Fonctionne IDENTIQUEMENT en dev et en production (exécutable
        PyInstaller) : on relance sys.executable (= l'app elle-même une
        fois packagée) avec la variable d'environnement LMGC90_WORKER
        positionnée sur le script à exécuter. main.py détecte cette
        variable AVANT de créer QApplication/MainWindow, exécute juste
        le script via runpy puis quitte (sys.exit(0)) — donc aucune
        nouvelle fenêtre / instance de l'application ne s'ouvre.
        """
        if not self.controller.project_path:
            QMessageBox.warning(self, "Attention", "Enregistrez d'abord le projet")
            return self._on_save_project_as()

        script_path = self.controller.project_path.parent / f"{self.controller.state.name}.py"

        if not script_path.exists():
            reply = QMessageBox.question(
                self, "Script introuvable",
                f"Le script '{script_path.name}' n'existe pas encore.\n\n"
                "Voulez-vous le générer maintenant ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_generate_script()
            if not script_path.exists():
                return

        if self._script_process is not None \
                and self._script_process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(
                self, "Script en cours",
                "Un script est déjà en cours d'exécution. Attendez sa fin."
            )
            return

        self._run_script_subprocess(script_path)

    def _run_script_subprocess(self, script_path: Path):
        """Lance script_path en tant que sous-processus 'worker' (cf. main.py)."""
        proc = QProcess(self)

        # En dev, sys.executable est l'interpréteur Python : il faut lui
        # repasser les arguments de lancement (sys.argv, dont argv[0] =
        # chemin de main.py) pour qu'il réexécute bien main.py.
        # En production (PyInstaller), sys.executable EST l'application
        # elle-même : pas d'argument supplémentaire nécessaire.
        if getattr(sys, 'frozen', False):
            proc.setProgram(sys.executable)
            proc.setArguments([])
        else:
            proc.setProgram(sys.executable)
            proc.setArguments(list(sys.argv))

        proc.setWorkingDirectory(str(script_path.parent))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("LMGC90_WORKER", str(script_path))
        proc.setProcessEnvironment(env)

        self._script_log_dialog = self._make_script_log_dialog(script_path.name)
        self._script_log_dialog.show()

        proc.readyReadStandardOutput.connect(lambda: self._on_script_stdout(proc))
        proc.finished.connect(
            lambda code, status: self._on_script_finished(script_path, code, status)
        )
        proc.errorOccurred.connect(
            lambda err: _log.warning(f"Erreur lancement sous-processus script : {err}")
        )

        self._script_process = proc
        self.statusBar().showMessage(f"⏳ Exécution de {script_path.name}...")
        proc.start()

    def _make_script_log_dialog(self, title: str) -> QDialog:
        """Petite fenêtre non-modale affichant la sortie live du script."""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"▶️ Exécution — {title}")
        dlg.resize(750, 480)
        layout = QVBoxLayout(dlg)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(
            "QTextEdit { font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 9pt; background:#1e1e2e; color:#c8d0e8; }"
        )
        layout.addWidget(text_edit)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dlg.close)
        layout.addWidget(close_btn)

        dlg.text_edit = text_edit
        return dlg

    def _on_script_stdout(self, proc: QProcess):
        data = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='replace')
        if self._script_log_dialog is not None:
            self._script_log_dialog.text_edit.append(data.rstrip('\n'))

    def _on_script_finished(self, script_path: Path, exit_code: int, exit_status):
        self._script_process = None

        if self._script_log_dialog is not None:
            if exit_code == 0:
                self._script_log_dialog.text_edit.append(
                    "\n✅ Script terminé avec succès (code 0)."
                )
            else:
                self._script_log_dialog.text_edit.append(
                    f"\n❌ Le script s'est terminé avec le code {exit_code}."
                )

        if exit_code == 0:
            self.statusBar().showMessage(f"✅ {script_path.name} terminé avec succès", 5000)

            # Si une factory a généré ses métadonnées, proposer de les charger
            json_path = script_path.parent / "factory_avatars_metadata.json"
            if json_path.exists():
                reply = QMessageBox.question(
                    self, "Avatars de factory détectés",
                    "Le script a généré factory_avatars_metadata.json.\n"
                    "Voulez-vous charger ces avatars dans le projet maintenant ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._on_load_factory_avatars()
        else:
            self.statusBar().showMessage(
                f"❌ {script_path.name} a échoué (code {exit_code})", 8000
            )

    def _on_load_factory_avatars(self):
        """Charge les métadonnées des avatars de factory et les ajoute au projet"""
        if not self.controller.project_path:
            QMessageBox.warning(
                self, "Attention", 
                "Enregistrez d'abord le projet"
            )
            return self._on_save_project_as()
        
        # Chercher factory_avatars_metadata.json dans le même répertoire que le projet
        json_path = self.controller.project_path.parent / "factory_avatars_metadata.json"
        
        if not json_path.exists():
            QMessageBox.warning(
                self, "Fichier non trouvé",
                f"Le fichier factory_avatars_metadata.json n'existe pas.\n\n"
                f"Chemin attendu:\n{json_path}\n\n"
                f"Assurez-vous que pre.py a été exécuté dans le répertoire:\n"
                f"{self.controller.project_path.parent}"
            )
            return
        
        try:
            self.statusBar().showMessage("Chargement des avatars de factory...", 2000)
            QApplication.processEvents()
            
            # Charger les factory avatars via le controller
            indices = self.controller.load_factory_avatars_from_json(str(json_path))
            
            # Rafraîchir l'interface
            self.avatar_tab.refresh()
            self.viewer_tab.refresh()
            
            if indices:
                QMessageBox.information(
                    self, "Succès",
                    f"✅ {len(indices)} avatar(s) de factory chargé(s) avec succès !\n\n"
                    f"Indices: {indices}\n\n"
                    f"Les avatars sont maintenant visibles dans l'arborescence du projet.\n"
                    f"Vous pouvez leur appliquer des lois de contact ou les utiliser dans\n"
                    f"d'autres workflows."
                )
            else:
                QMessageBox.warning(
                    self, "Aucun avatar",
                    "Aucun avatar de factory trouvé dans le fichier JSON."
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur",
                f"Chargement des avatars échoué :\n{e}"
            )
    
    def _on_convert_script(self):
        dialog = ConvertDialog(self)
        dialog.exec()
    

    def _launch_visu(self):
        from pylmgc90 import pre
        pre.visuAvatars(
            self.controller._bodies_container,
            with_axis=True,
            drvdof_color=[1., 0., 0.]
        )

    def _on_lmgc_visualization(self):
        try:
            if not self.controller._pylmgc_bodies:
                QMessageBox.warning(
                    self,
                    "Attention",
                    "Aucun avatar à visualiser"
                )
                return

            thread = threading.Thread(
                target=self._launch_visu,
                daemon=True
            )
            thread.start()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Visualisation échouée :\n{e}"
            )
    
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
    

    # =======Menu calcul ===================
    def _on_show_app_log(self):
        """Ouvre le journal global de l'application dans une fenêtre dédiée."""
        from ..gui.dialogs.app_log_dialog import AppLogDialog
        dlg = AppLogDialog(parent=self)
        dlg.show()

    def _on_show_logs(self):
        """Switche vers l'onglet Calcul et affiche le panneau de logs."""
        self._add_tab('compute')
        self.tabs.setCurrentWidget(self.compute_tab)
        self.compute_tab.show_log_panel()

    def _on_compute_setup(self):
        """Ouvre l'onglet calcul"""
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) is self.compute_tab:
                self.tabs.setCurrentIndex(i)
                return
        self._add_tab('compute')
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) is self.compute_tab:
                self.tabs.setCurrentIndex(i)
                return

    def _on_run_compute(self):
        """Lance le calcul"""
        if not self.controller.project_path:
            QMessageBox.warning(self, "Projet", "Enregistrez d'abord le projet")
            return self._on_save_project_as()
        
        try:
            self.compute_tab.run_computation()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Calcul échoué:\n{e}")

    def _on_generate_compute_script(self):
        """Génère le script de calcul"""
        if not self.controller.project_path:
            QMessageBox.warning(self, "Projet", "Enregistrez d'abord le projet")
            return self._on_save_project_as()
        
        script_path = self.controller.project_path.parent / "command.py"
        
        try:
            from ..utils.compute_script_generator import ComputeScriptGenerator
            generator = ComputeScriptGenerator(self.controller)
            generator.generate(script_path, self.compute_tab.get_parameters())
            
            QMessageBox.information(self, "Succès", f"Script généré:\n{script_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée:\n{e}")

    # ========== RAFRAÎCHISSEMENT ==========
    
    def _refresh_all(self):
        """Rafraîchit toute l'interface"""
        self.tree_view.refresh()
 
        for tab in [self.material_tab, self.model_tab, self.avatar_tab,
                    self.empty_avatar_tab, self.loop_tab, self.dof_tab
                    , self.contact_tab, self.visibility_tab, self.granulo_tab,
                    self.postpro_tab]:
            if hasattr(tab, 'refresh'):
                if tab is self.granulo_tab:
                    tab.refresh(full_refresh=True)
                else :     
                    tab.refresh()