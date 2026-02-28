"""
Fenêtre principale de l'application.
Interface entre l'utilisateur et le contrôleur.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QPushButton, QDockWidget,
    QTabWidget, QMessageBox, QFileDialog, QApplication,
    QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from pathlib import Path

from ..controllers.project_controller import ProjectController
from ..core.models import ValidationError
from .tabs import (
    MaterialTab, ModelTab, AvatarTab, EmptyAvatarTab, AvatarLibraryTab, LoopTab,
    GranuloTab, DOFTab, ContactTab, VisibilityTab, PostProTab, ComputeTab, ViewerTab
)
from .tree_view import ModelTreeView
from ..core.models import UnitSystem
from ..gui.dialogs.fast_granulo_dialg import GranuloFastDialog


class MainWindow(QMainWindow):
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
        
        # Configuration fenêtre
        self.setWindowTitle(f"LMGC90_GUI v0.3.0 - {self.controller.state.name}")
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
    
        wizard_action = QAction("🧙 Assistant de Projet...", self)
        wizard_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        wizard_action.triggered.connect(self._on_project_wizard)
        file_menu.addAction(wizard_action)
        

        wizard_action = QAction("🧙 Assistant de granulométrie...", self)
        wizard_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
        wizard_action.triggered.connect(self._on_granulo_wizard)
        file_menu.addAction(wizard_action)

        fast_granulo = QAction(" ⚡ Génération granulométrie numpy... (bêta)", self)
        fast_granulo.triggered.connect(self._open_fast_granulo)
        file_menu.addAction(fast_granulo)

        wizard_action = QAction("🧙 Assistant de déformable...", self)
        wizard_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        wizard_action.triggered.connect(self._on_deformable_wizard)
        file_menu.addAction(wizard_action)


        file_menu.addSeparator()
        
        quit_action = QAction("Quitter", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Menu Outils
        tools_menu = menubar.addMenu("Outils")
        #Préférences
        prefs_action = QAction("⚙️ Préférences...", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))  # Raccourci standard
        prefs_action.triggered.connect(self._on_preferences)
        tools_menu.addAction(prefs_action)
        tools_menu.addSeparator()

        datbox_action = QAction("Générer DATBOX", self)
        datbox_action.triggered.connect(self._on_generate_datbox)
        tools_menu.addAction(datbox_action)

        script_action = QAction("Générer Script Python", self)
        script_action.triggered.connect(self._on_generate_script)
        tools_menu.addAction(script_action)
        
        tools_menu.addSeparator()
        
        vars_action = QAction("Variables dynamiques", self)
        vars_action.triggered.connect(self._on_dynamic_vars)
        tools_menu.addAction(vars_action)
        
        # Menu calcul
        compute_menu = menubar.addMenu("Calcul")
        
        setup_action = QAction("⚙️ Paramètres de Calcul", self)
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
            action.triggered.connect(lambda checked, tid=tab_id: self._add_tab(tid))
        
        tabs_menu.addSeparator()
        
        close_others_action = tabs_menu.addAction("❌ Fermer les autres")
        close_others_action.triggered.connect(self._close_other_tabs)
        
        close_all_action = tabs_menu.addAction("🗑️ Fermer tous (sauf essentiels)")
        close_all_action.triggered.connect(self._close_all_tabs)
        
        tabs_menu.addSeparator()
        
        defaults_action = tabs_menu.addAction("🔄 Onglets par défaut")
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
        #connect le signal
        self.tree_view.item_selected.connect(self._on_tree_item_selected)

    def  _on_tree_item_selected(self, item_type: str, item_data):
        """Quand un élément est sélectionné dans l'arbre"""
        if item_type == "material":
            # Charger le matériau et switcher vers l'onglet
            material = self.controller.get_material(item_data)
            if material:
                self.tabs.setCurrentWidget(self.material_tab)
                if hasattr(self.material_tab, 'load_for_edit') : 
                    self.material_tab.load_for_edit(material)
        elif item_type == "model":
            model = self.controller.get_model(item_data)
            if model:
                self.tabs.setCurrentWidget(self.model_tab)
                self.model_tab.load_for_edit(model)
        
        elif item_type == "avatar":
            avatar = self.controller.get_avatar(item_data)
            if avatar:
                from ..core.models import AvatarType
                if avatar.avatar_type == AvatarType.EMPTY_AVATAR:
                    self.tabs.setCurrentWidget(self.empty_avatar_tab)
                    self.empty_avatar_tab.load_for_edit(item_data, avatar)
                else:
                    self.tabs.setCurrentWidget(self.avatar_tab)
                    self.avatar_tab.load_for_edit(item_data, avatar)
        
        elif item_type == "contact_law":
            law = self.controller.get_contact_law(item_data)
            if law:
                self.tabs.setCurrentWidget(self.contact_tab)
                self.contact_tab.load_for_edit(law)
        
        elif item_type == "visibility":
            rule = self.controller.get_visibility_rule(item_data)
            if rule:
                self.tabs.setCurrentWidget(self.visibility_tab)
                self.visibility_tab.load_for_edit(item_data, rule)

        elif item_type == "dof_operation":
            operation = self.controller.get_dof_operation(item_data)
            if operation:
                self.tabs.setCurrentWidget(self.dof_tab)
                self.dof_tab.load_for_edit(item_data, operation)

        elif item_type == "loop":   
            loop = self.controller.get_loop(item_data)
            print(item_data)
            if loop:
                self.tabs.setCurrentWidget(self.loop_tab)
                self.loop_tab.load_for_edit(item_data)

        elif item_type == "granulo":
            granulo = self.controller.get_granulo(item_data)
            if granulo:
                self.tabs.setCurrentWidget(self.granulo_tab)
                self.granulo_tab.load_for_edit(item_data, granulo)

        elif item_type == "postpro":
            postpro = self.controller.get_postpro_command(item_data)
            if postpro:
                self.tabs.setCurrentWidget(self.postpro_tab)
                self.postpro_tab.load_for_edit(postpro)
    
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
        splitter.setSizes([700, 300])
    
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
        self.render_widget.setLayout(layout)
        self.render_widget.setMinimumHeight(150)
    
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
        self.model_tab.dimension_changed.connect(self.avatar_tab._update_avatar_types)
        #self.model_tab.dimension_changed.connect(self.empty_avatar_tab.sync_dimension)

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
        self.avatar_tab.avatar_created.connect(self.viewer_tab.refresh)
        self.avatar_tab.avatar_updated.connect(self.viewer_tab.refresh)
        self.avatar_tab.avatar_deleted.connect(self.viewer_tab.refresh)
        self.loop_tab.loop_generated.connect(self.viewer_tab.refresh)
        self.granulo_tab.granulo_generated.connect(self.viewer_tab.refresh)
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
            self.setWindowTitle(f"LMGC90_GUI v0.3.0 - {name}")
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
                self.setWindowTitle(f"LMGC90_GUI v0.3.0 - {self.controller.state.name}")
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
    
 

    # ======Tabs======================

    def _add_tab(self, tab_id: str):
        """Ajoute un onglet s'il n'est pas déjà ouvert"""
        if tab_id not in self.all_tabs:
            return
        
        title, widget, icon = self.all_tabs[tab_id]
        
        # Vérifier si déjà ouvert
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) == widget:
                self.tabs.setCurrentIndex(i)
                return
        
        # Ajouter l'onglet
        index = self.tabs.addTab(widget, f"{icon} {title}")
        self.tabs.setCurrentIndex(0)
    def _on_tab_close_requested(self, index : int): 
        """Gère la fermeture d'un onglet"""
        widget = self.tabs.widget(index)
        tab_name = self.tabs.tabText(index)
        
        # Empêcher la fermeture de certains onglets essentiels
        essential_tabs = [self.material_tab, self.model_tab]
        
        if widget in essential_tabs:
            QMessageBox.warning(
                self, "Onglet essentiel",
                f"L'onglet '{tab_name}' ne peut pas être fermé car il est essentiel."
            )
            return
    
        # Fermer l'onglet (ne pas le supprimer, juste le retirer)
        self.tabs.removeTab(index)
    
    def _close_other_tabs(self):
        """Ferme tous les onglets sauf celui actif"""
        current_index = self.tabs.currentIndex()
        current_widget = self.tabs.widget(current_index)
        
        # Fermer en ordre inverse pour garder les indices valides
        for i in range(self.tabs.count() - 1, -1, -1):
            if i != current_index:
                widget = self.tabs.widget(i)
                essential_tabs = [self.material_tab, self.model_tab, self.compute_tab]
                
                if widget not in essential_tabs:
                    self.tabs.removeTab(i)

    def _close_all_tabs(self):
        """Ferme tous les onglets non essentiels"""
        essential_tabs = [self.material_tab, self.model_tab, self.compute_tab]
        
        # Fermer en ordre inverse
        for i in range(self.tabs.count() - 1, -1, -1):
            widget = self.tabs.widget(i)
            if widget not in essential_tabs:
                self.tabs.removeTab(i)

    def _reopen_default_tabs(self):
        """Rouvre les onglets par défaut"""
        default_tabs = ['material', 'model', 'avatar', 'dof', 'visibility', 'postpro']
        
        for tab_id in default_tabs:
            self._add_tab(tab_id)
   
    # =======Menu Outils =============
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
            "LMGC90_GUI v0.3.0\n\n"
            "Architecture MVC refactorisée\n"
            "par Zerourou B.\n\n"
            "© 2025 - Open Source"
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

    def _update_recent_menu(self):
        """Met à jour le menu des projets récents"""
        if not hasattr(self, 'recent_menu'):
            return
        self.recent_menu.clear()
        
        # Vérifier que preferences existe
        if not hasattr(self.controller.state, 'preferences'):
            no_recent = self.recent_menu.addAction("(Aucun projet récent)")
            no_recent.setEnabled(False)
            return
        recent_projects = self.controller.state.preferences.recent_projects
        
        if not recent_projects:
            no_recent = self.recent_menu.addAction("(Aucun projet récent)")
            no_recent.setEnabled(False)
            return
        
        for project_path in recent_projects[:10]:  # Limiter à 10
            if project_path.exists():
                action = self.recent_menu.addAction(f"📄 {project_path.name}")
                action.triggered.connect(lambda checked, p=project_path: self._open_recent_project(p))
            else:
                # Projet introuvable
                action = self.recent_menu.addAction(f"❌ {project_path.name} (introuvable)")
                action.setEnabled(False)
        
        self.recent_menu.addSeparator()
        
        clear_action = self.recent_menu.addAction("🗑️ Effacer l'historique")
        clear_action.triggered.connect(self._clear_recent_projects)

    def _open_recent_project(self, filepath: Path):
        """Ouvre un projet récent"""
        try:
            self.controller.load_project(filepath)
            self.setWindowTitle(f"LMGC90_GUI v0.3.0 - {self.controller.state.name}")
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
    
    # ========Wizard ===================================

    def _on_project_wizard(self):
        """Lance l'assistant de configuration"""
        from ..gui.dialogs.setup_wizard import ProjectSetupWizard
        
        wizard = ProjectSetupWizard(self.controller, self)
        if wizard.exec():
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
    

    # =======Menu calcul ===================
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
                   self.empty_avatar_tab, self.loop_tab, self.granulo_tab,
                   self.dof_tab, self.contact_tab, self.visibility_tab,
                   self.postpro_tab]:
            if hasattr(tab, 'refresh'):
                if tab is self.granulo_tab :
                    tab.refresh(full_refresh=True)
                tab.refresh()