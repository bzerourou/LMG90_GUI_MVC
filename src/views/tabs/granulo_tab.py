# ============================================================================
# Onglet Granulométrie 
# ============================================================================
"""
Onglet pour générer des distributions granulométriques.
Version avec support threading pour éviter les plantages avec >1000 particules.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox, QLabel, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QMenu, QHBoxLayout, QScrollArea,
    QProgressDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor

from ...core.models import GranuloGeneration
from ...core.validators import ValidationError
from ...core.models import Avatar, AvatarType, AvatarOrigin
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab

from ...core.workers.granulo_worker import GranuloWorker

import gc

class GranuloTab(BaseTab):
    """Onglet granulo ultra-optimisé avec création progressive"""
    
    granulo_generated = pyqtSignal()
    granulo_deleted = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        
        # Worker pour calculs
        self.worker = None
        
        # Timer pour création progressive des avatars
        self.creation_timer = QTimer()
        self.creation_timer.timeout.connect(self._create_next_avatar)
        
        # Données en attente de création
        self.pending_particles = []
        self.created_indices = []
        self.current_particle_index = 0
        self.current_config = None
        self.batch_size = 50  # Taille du batch (adaptative)
        
        # Flag d'annulation
        self._user_canceled = False
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface (identique à avant)"""
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)
        
        tree_label = QLabel("<b>📋 Dépôts Granulométriques Existants</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Type", "Nb Part.", "Rayons", "Groupe"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 80)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(150)
        layout.addWidget(self.tree)
        
        tree_btn_layout = QHBoxLayout()
        delete_tree_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_tree_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_tree_btn)
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)
        
        dist_group = QGroupBox("1. Distribution des Particules")
        dist_form = QFormLayout()
        
        self.nb_input = QLineEdit("200")
        dist_form.addRow("Nombre de particules :", self.nb_input)
        
        self.rmin_input = QLineEdit("0.05")
        dist_form.addRow("Rayon min :", self.rmin_input)
        
        self.rmax_input = QLineEdit("0.15")
        dist_form.addRow("Rayon max :", self.rmax_input)
        
        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("Graine aléatoire (optionnel)")
        dist_form.addRow("Seed :", self.seed_input)

        self.dist_only_check = QCheckBox(
            "Distribution uniquement — sans dépôt ni création d'avatars"
        )
        self.dist_only_check.setToolTip(
            "Génère seulement la distribution de rayons (granulo_Random).\n"
            "Aucun avatar n'est créé. La distribution est enregistrée pour référence."
        )
        self.dist_only_check.toggled.connect(self._on_dist_only_toggled)
        dist_form.addRow("", self.dist_only_check)

        dist_group.setLayout(dist_form)
        layout.addWidget(dist_group)
        
        self.container_group = QGroupBox("2. Géométrie du Dépôt")
        container_group = self.container_group
        container_layout = QVBoxLayout()
        
        container_form = QFormLayout()
        
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Box2D", "Disk2D", "Couette2D", "Drum2D"])
        container_form.addRow("Type de conteneur :", self.shape_combo)
        
        container_layout.addLayout(container_form)
        
        self.params_widget = QWidget()
        self.params_layout = QFormLayout()
        self.params_widget.setLayout(self.params_layout)
        container_layout.addWidget(self.params_widget)
        
        self.lx_input = QLineEdit("4.0")
        self.ly_input = QLineEdit("4.0")
        self.r_input = QLineEdit("2.0")
        self.rint_input = QLineEdit("2.0")
        self.rext_input = QLineEdit("4.0")
        
        container_group.setLayout(container_layout)
        layout.addWidget(container_group)
        
        self.phys_group = QGroupBox("3. Propriétés Physiques")
        phys_group = self.phys_group
        phys_form = QFormLayout()
        
        self.material_combo = QComboBox()
        phys_form.addRow("Matériau :", self.material_combo)
        
        self.model_combo = QComboBox()
        phys_form.addRow("Modèle :", self.model_combo)
        
        self.avatar_combo = QComboBox()
        phys_form.addRow("Type d'avatar :", self.avatar_combo)
        
        self.color_input = QLineEdit("BLUEx")
        phys_form.addRow("Couleur :", self.color_input)
        
        phys_group.setLayout(phys_form)
        layout.addWidget(phys_group)
        
        self.store_check = QCheckBox("Stocker le dépôt dans un groupe nommé")
        self.store_check.setChecked(True)
        layout.addWidget(self.store_check)
        
        group_form = QFormLayout()
        self.group_name_input = QLineEdit("depot_granulo")
        group_form.addRow("Nom du groupe :", self.group_name_input)
        layout.addLayout(group_form)
        
        # Avertissement
        warning_label = QLabel(
            "<i>⚡ Génération avec dépôt granuloRandom.<br>"
            "Création par batches adaptatifs (10-100 selon volume).<br>"
            "Temps: ~0.5-1s/100 particules en affichage </i>"
        )
        warning_label.setStyleSheet("color: #00AA00; padding: 5px; font-weight: bold;")
        layout.addWidget(warning_label)
        
        btn_layout = QHBoxLayout()
        
        self.gen_btn = QPushButton("✅ Générer le Dépôt")
        self.gen_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        self.gen_btn.clicked.connect(self._on_generate_optimized)
        btn_layout.addWidget(self.gen_btn)
        
        clear_btn = QPushButton("🔄 Réinitialiser")
        clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        self.add_expression_help_label(layout)
        self.setLayout(main_layout)
        self._update_container_params("Box2D")
    
    def _connect_signals(self):
        self.shape_combo.currentTextChanged.connect(self._update_container_params)
        self.tree.itemDoubleClicked.connect(self._show_info)

    def _on_dist_only_toggled(self, checked: bool):
        """Active/désactive géométrie et propriétés selon le mode distribution seule."""
        self.container_group.setEnabled(not checked)
        self.phys_group.setEnabled(not checked)
        if checked:
            self.gen_btn.setText("✅ Générer la Distribution")
            self.container_group.setStyleSheet(
                "QGroupBox { color: #aaa; border-color: #ccc; }"
                "QGroupBox::title { color: #aaa; }"
            )
            self.phys_group.setStyleSheet(
                "QGroupBox { color: #aaa; border-color: #ccc; }"
                "QGroupBox::title { color: #aaa; }"
            )
        else:
            self.gen_btn.setText("✅ Générer le Dépôt")
            self.container_group.setStyleSheet("")
            self.phys_group.setStyleSheet("")
    
    def _update_container_params(self, shape):
        """Met à jour les paramètres du conteneur"""
        while self.params_layout.count() > 0:
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        if shape == "Box2D":
            self.params_layout.addRow("Largeur (lx) :", self.lx_input)
            self.params_layout.addRow("Hauteur (ly) :", self.ly_input)
            self.lx_input.show()
            self.ly_input.show()
        elif shape in ["Disk2D", "Drum2D"]:
            self.params_layout.addRow("Rayon (r) :", self.r_input)
            self.r_input.show()
        elif shape == "Couette2D":
            self.params_layout.addRow("Rayon int (rint) :", self.rint_input)
            self.params_layout.addRow("Rayon ext (rext) :", self.rext_input)
            self.rint_input.show()
            self.rext_input.show()
    
    def _show_context_menu(self, position):
        """Menu contextuel"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete)
        menu.addSeparator()
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    # ========== GÉNÉRATION OPTIMISÉE ==========
    
    def _on_generate_optimized(self):
        """Lance la génération ultra-optimisée"""
        try:
            # Validation commune
            nb = self.eval_int(self.nb_input.text(), default=50, field_name="Nombre de particules")
            rmin = self.eval_float(self.rmin_input.text(), default=0.05, field_name="Rayon min")
            rmax = self.eval_float(self.rmax_input.text(), default=2*rmin, field_name="Rayon max")
            seed_text = self.seed_input.text().strip()
            seed = self.eval_int(seed_text, default=None, field_name="Seed") if seed_text else None

            # ── Mode distribution uniquement ──────────────────────────────────
            if self.dist_only_check.isChecked():
                self._generate_distribution_only(nb, rmin, rmax, seed)
                return

            # ── Mode dépôt complet ────────────────────────────────────────────
            if nb > 2000:
                QMessageBox.information(self, "Attention", "⚠️ Actuellement LMGC90_GUI ne peut générer plus de 1500 particules ")
                return

            material = self.material_combo.currentText()
            model = self.avatar_combo.currentData()

            if not material or not model:
                QMessageBox.warning(self, "Erreur", "Veuillez créer un matériau et un modèle d'abord")
                return

            # Si l'affichage individuel est désactivé, le groupe est OBLIGATOIRE
            show_individually = getattr(
                getattr(self.controller.state, 'preferences', None),
                'show_granulo_individually', True
            )
            if not show_individually:
                group_name = self.group_name_input.text().strip()
                if not group_name:
                    QMessageBox.warning(
                        self, "Groupe obligatoire",
                        "L'affichage individuel est désactivé dans les Préférences.\n"
                        "Vous devez entrer un nom de groupe avant de générer."
                    )
                    self.group_name_input.setFocus()
                    return
            
            # Paramètres conteneur
            shape = self.shape_combo.currentText()
            if shape == "Box2D":
                container_params = {
                    'lx': self.eval_float(self.lx_input.text(), default=4.0, field_name="Largeur"),
                    'ly': self.eval_float(self.ly_input.text(), default=4.0, field_name="Hauteur")
                }
            elif shape in ["Disk2D", "Drum2D"]:
                container_params = {'r': self.eval_float(self.r_input.text(), default=2.0, field_name="Rayon")}
            elif shape == "Couette2D":
                container_params = {
                    'rint': self.eval_float(self.rint_input.text(), default=2.0, field_name="Rayon intérieur"),
                    'rext': self.eval_float(self.rext_input.text(), default=4.0, field_name="Rayon extérieur")
                }
            else:
                container_params = {}
            
            # Config
            config = GranuloGeneration(
                nb_particles=nb,
                radius_min=rmin,
                radius_max=rmax,
                container_type=shape,
                container_params=container_params,
                model_name=self.model_combo.currentText(),
                material_name=material,
                avatar_type=model,
                color=self.color_input.text().strip(),
                seed=seed,
                group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
            )
            
            # Stocker la config
            self.current_config = config
            
            # Réinitialiser le flag d'annulation
            self._user_canceled = False
            
            # Créer un label de progression au lieu du dialogue
            if not hasattr(self, 'progress_label'):
                self.progress_label = QLabel(self)
                self.progress_label.setStyleSheet(
                    "QLabel { background-color: #E3F2FD; border: 2px solid #2196F3; "
                    "border-radius: 5px; padding: 10px; font-weight: bold; }"
                )
                self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.progress_label.setText("⏳ Phase 1/2: Calcul du dépôt granulométrique...)")
            self.progress_label.setGeometry(
                self.width() // 2 - 200,
                self.height() // 2 - 50,
                400,
                100
            )
            self.progress_label.show()
            self.progress_label.raise_()
            
            # Désactiver le bouton
            self.gen_btn.setEnabled(False)
            
            # Lancer le worker pour CALCULS SEULEMENT
            self.worker = GranuloWorker(config)
            self.worker.progress_updated.connect(self._on_calc_progress)
            self.worker.data_ready.connect(self._on_data_ready)
            self.worker.error_occurred.connect(self._on_error)
            self.worker.start()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de démarrer:\n{e}")
    
    def _generate_distribution_only(self, nb: int, rmin: float, rmax: float, seed):
        """
        Génère uniquement la distribution de rayons via GranuloGenerator.generate_radii.
        Aucun avatar n'est créé. La distribution est enregistrée dans le projet.
        """
        from ...core.generators import GranuloGenerator

        if rmin <= 0 or rmax <= 0:
            QMessageBox.warning(self, "Validation", "Rayon min et max doivent être positifs.")
            return
        if rmin > rmax:
            QMessageBox.warning(self, "Validation", "Rayon min doit être ≤ rayon max.")
            return

        group_name = (
            self.group_name_input.text().strip()
            if self.store_check.isChecked()
            else None
        )

        config = GranuloGeneration(
            nb_particles=nb,
            radius_min=rmin,
            radius_max=rmax,
            container_type="Distribution",
            container_params={'distribution_only': True},
            model_name="",
            material_name="",
            avatar_type="",
            color="",
            seed=seed,
            group_name=group_name,
            generated_ids=[],
        )

        try:
            radii = GranuloGenerator.generate_radii(config)
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur",
                f"Erreur lors de la génération des rayons :\n{e}"
            )
            return

        r_mean = float(radii.mean())
        r_std  = float(radii.std())

        self.controller.state.granulo_generations.append(config)
        self.granulo_generated.emit()
        self.refresh(full_refresh=True)

        QMessageBox.information(
            self, "Distribution générée",
            f"✅ Distribution de {len(radii)} rayons enregistrée.\n\n"
            f"  Rayon min    : {rmin:.4g}\n"
            f"  Rayon max    : {rmax:.4g}\n"
            f"  Rayon moyen  : {r_mean:.4g}\n"
            f"  Écart-type   : {r_std:.4g}\n"
            + (f"  Groupe : {group_name}" if group_name else "  (pas de groupe)")
        )

    def _on_calc_progress(self, current, total, message):
        """Progression des calculs"""
        if hasattr(self, 'progress_label') and self.progress_label.isVisible():
            try:
                percent = int(current * 100 / total) if total > 0 else 0
                self.progress_label.setText(
                    f"⏳ Phase 1/2: Calcul du dépôt...\n"
                    f"{message}\n"
                    f"Progression: {percent}%"
                )
            except:
                pass
    
    def _on_data_ready(self, particles_data):
        """Les positions sont calculées, lancer la création par batches"""
        # Stocker les données
        self.pending_particles = particles_data
        self.created_indices = []
        self.current_particle_index = 0
        
        # Mettre à jour le label
        if hasattr(self, 'progress_label') and self.progress_label.isVisible():
            self.progress_label.setText(
                "⚡ Phase 2/2: Création des avatars...\n"
                "0%"
            )
        
        # Nettoyer le worker
        if self.worker:
            self.worker.wait()
            self.worker.deleteLater()
            self.worker = None
        
        # Forcer garbage collection
        gc.collect()

        # Bloquer uniquement le tree (pas tout l'onglet — sinon l'UI fige)
        if hasattr(self, 'tree'):
            self._old_updates_enabled = self.updatesEnabled()
            self.setUpdatesEnabled(False)  # Bloquer le rendu de l'onglet

        # OPTIMISATION : Créer par BATCHES au lieu d'un par un
        # Taille du batch adaptative selon le nombre total
        total = len(particles_data)
        if total < 200:
            self.batch_size = 10      # Petit nombre : batches de 10
        elif total < 1000:
            self.batch_size = 50      # Moyen : batches de 50
        else:
            self.batch_size = 100     # Gros volume : batches de 100
        
        # Démarrer le timer de création par batches
        # Intervalle 0 = aussi rapide que possible mais UI reste réactive
        self.creation_timer.start(0)
    
    def _create_next_avatar(self):
        """Crée un BATCH d'avatars (au lieu d'un seul) pour accélérer"""
        if self.current_particle_index >= len(self.pending_particles):
            # Terminé !
            self.creation_timer.stop()
            self._on_creation_completed()
            return
        
        try:
            # OPTIMISATION : Créer un BATCH d'avatars d'un coup
            batch_end = min(
                self.current_particle_index + self.batch_size,
                len(self.pending_particles)
            )
            
            # Désactiver temporairement les signaux state_changed via flag interne
            self.controller._batch_mode = True
            
            for i in range(self.current_particle_index, batch_end):
                particle = self.pending_particles[i]
                
                avatar = Avatar(
                    avatar_type=AvatarType(self.current_config.avatar_type),
                    center=particle['center'],
                    material_name=self.current_config.material_name,
                    model_name=self.current_config.model_name,
                    color=self.current_config.color,
                    origin=AvatarOrigin.GRANULO,
                    radius=particle['radius']
                )
                
                # Ajouter au controller (sans émettre de signaux)
                # Respecter la préférence : créer ou non les objets pylmgc lors d'une génération massive
                create_pylmgc = getattr(
                    getattr(self.controller.state, 'preferences', None),
                    'create_pylmgc_on_generate', True
                )
                idx = self.controller.add_avatar(avatar, create_pylmgc=create_pylmgc)
                self.created_indices.append(idx)
            
            # Réactiver les signaux
            self.controller._batch_mode = False
            
            # Mettre à jour l'index
            self.current_particle_index = batch_end
            
            # Mettre à jour la progression
            if hasattr(self, 'progress_label') and self.progress_label.isVisible():
                try:
                    total = len(self.pending_particles)
                    percent = int(self.current_particle_index * 100 / total) if total > 0 else 0
                    # Mettre à jour moins souvent pour accélérer
                    if self.current_particle_index % 50 == 0 or self.current_particle_index == total:
                        self.progress_label.setText(
                            f"⚡ Phase 2/2: Création des avatars...\n"
                            f"Création: {self.current_particle_index}/{total} particules\n"
                            f"Progression: {percent}%"
                        )
                except:
                    pass
            
            # Garbage collection tous les 500 avatars (moins fréquent)
            if self.current_particle_index % 500 == 0:
                gc.collect()
                
        except Exception as e:
            self.creation_timer.stop()
            self._on_error(f"Erreur création avatar {self.current_particle_index}: {str(e)}")
    
    def _on_creation_completed(self):
        """Création terminée avec succès"""
        # Fermer le label de progression
        if hasattr(self, 'progress_label'):
            self.progress_label.hide()
        
        # réactiver les updates du tree
        if hasattr(self, '_old_updates_enabled'):
            self.setUpdatesEnabled(self._old_updates_enabled)
        
        # S'assurer que le batch_mode est bien désactivé
        self.controller._batch_mode = False

        self.gen_btn.setEnabled(True)
        
        # Finaliser
        if self.current_config:
            # Convertir les positions (int) en avatar_ids stables (str)
            avatars = self.controller.state.avatars
            created_avatar_ids = [
                avatars[idx].avatar_id
                for idx in self.created_indices
                if idx < len(avatars)
            ]

            self.current_config.generated_ids = created_avatar_ids
            self.controller.state.granulo_generations.append(self.current_config)

            # Ajouter les avatar_ids (str) au groupe — plus des positions entières
            if self.current_config.group_name:
                if self.current_config.group_name not in self.controller.state.avatar_groups:
                    self.controller.state.avatar_groups[self.current_config.group_name] = []
                self.controller.state.avatar_groups[self.current_config.group_name].extend(
                    created_avatar_ids
                )
            
            # Émettre le signal UNE SEULE FOIS
            self.granulo_generated.emit()
            
            # Refresh UNE SEULE FOIS - SANS rafraîchir les combos (optimisation)
            self.refresh(full_refresh=True)
            
            # Message de succès NON-BLOQUANT avec label au lieu de QMessageBox
            if hasattr(self, 'progress_label'):
                self.progress_label.setStyleSheet(
                    "QLabel { background-color: #C8E6C9; border: 2px solid #4CAF50; "
                    "border-radius: 5px; padding: 10px; font-weight: bold; }"
                )
                msg = f"✅ {len(self.created_indices)} particules générées!"
                if self.current_config.group_name:
                    msg += f"\nGroupe: {self.current_config.group_name}"
                self.progress_label.setText(msg)
                self.progress_label.show()
                
                # Faire disparaître le message après 3 secondes
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(3000, self.progress_label.hide)
        
        # Nettoyer
        self.pending_particles = []
        self.created_indices = []
        self.current_config = None
        gc.collect()
    
    def _on_error(self, error_message):
        """Gestion des erreurs"""
        self.creation_timer.stop()
        
        # Réactiver les updates UI
        if hasattr(self, '_old_updates_enabled'):
            self.setUpdatesEnabled(self._old_updates_enabled)
        
        # S'assurer que le batch_mode est bien désactivé
        self.controller._batch_mode = False
        
        # Fermer le label de progression
        if hasattr(self, 'progress_label'):
            self.progress_label.hide()
        
        self.gen_btn.setEnabled(True)
        
        # Ne pas afficher de message si l'utilisateur a déjà annulé
        if not self._user_canceled:
            # Message NON-BLOQUANT avec label
            if hasattr(self, 'progress_label'):
                self.progress_label.setStyleSheet(
                    "QLabel { background-color: #FFCDD2; border: 2px solid #F44336; "
                    "border-radius: 5px; padding: 10px; font-weight: bold; }"
                )
                self.progress_label.setText(f"❌ Erreur:\n{error_message[:100]}")
                self.progress_label.show()
                
                # Disparaît après 5 secondes
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(5000, self.progress_label.hide)
        
        # Nettoyer
        self.pending_particles = []
        self.created_indices = []
        self.current_config = None
        
        if self.worker:
            self.worker.wait()
            self.worker.deleteLater()
            self.worker = None
        
        gc.collect()
    
    def _cancel_generation(self):
        """Annule la génération (si on veut ajouter un bouton Cancel plus tard)"""
        # Marquer comme annulé
        self._user_canceled = True
        
        self.creation_timer.stop()
        
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        # Fermer le label
        if hasattr(self, 'progress_label'):
            self.progress_label.hide()
        
        # Afficher le message d'annulation
        QMessageBox.information(self, "Annulé", "Génération annulée par l'utilisateur")
        
        # Réactiver le bouton
        self.gen_btn.setEnabled(True)
        
        # Nettoyer
        self.pending_particles = []
        self.created_indices = []
        self.current_config = None
        
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        
        gc.collect()
    
    # ========== AUTRES MÉTHODES (identiques) ==========
    
    def load_for_edit(self, index, granulo=None):
        """Charge un dépôt pour visualisation"""
        if granulo is None:
            granulo = self.controller.get_granulo(index)
        if not granulo:
            return
        
        self.nb_input.setText(str(granulo.nb_particles))
        self.rmin_input.setText(str(granulo.radius_min))
        self.rmax_input.setText(str(granulo.radius_max))
        self.shape_combo.setCurrentText(granulo.container_type)
        
        if granulo.container_type == "Box2D":
            self.lx_input.setText(str(granulo.container_params.get('lx', 4.0)))
            self.ly_input.setText(str(granulo.container_params.get('ly', 4.0)))
        elif granulo.container_type in ["Disk2D", "Drum2D"]:
            self.r_input.setText(str(granulo.container_params.get('r', 2.0)))
        elif granulo.container_type == "Couette2D":
            self.rint_input.setText(str(granulo.container_params.get('rint', 2.0)))
            self.rext_input.setText(str(granulo.container_params.get('rext', 4.0)))
        
        mat_idx = self.material_combo.findText(granulo.material_name)
        if mat_idx >= 0:
            self.material_combo.setCurrentIndex(mat_idx)
        
        mod_idx = self.model_combo.findText(granulo.model_name)
        if mod_idx >= 0:
            self.model_combo.setCurrentIndex(mod_idx)
        
        for i in range(self.avatar_combo.count()):
            if self.avatar_combo.itemData(i) == granulo.avatar_type:
                self.avatar_combo.setCurrentIndex(i)
                break
        
        self.color_input.setText(granulo.color)
        if granulo.seed:
            self.seed_input.setText(str(granulo.seed))
        if granulo.group_name:
            self.store_check.setChecked(True)
            self.group_name_input.setText(granulo.group_name)
    
    def _on_delete(self):
        """Supprime un dépôt"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un dépôt")
            return
        
        granulo_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        granulo = self.controller.get_granulo(granulo_idx)
        if not granulo:
            return
        
        nb_avatars = len(granulo.generated_ids)
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer le dépôt #{granulo_idx + 1} ?\n\n"
            f"⚠️ Cela supprimera également {nb_avatars} avatar(s) généré(s).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.remove_granulo(granulo_idx):
                self.granulo_deleted.emit()
                self.refresh(full_refresh=True)
                QMessageBox.information(self, "Succès", "✅ Dépôt et avatars supprimés")
    
    def _show_info(self):
        """Affiche les infos d'un dépôt"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        granulo_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        granulo = self.controller.get_granulo(granulo_idx)
        if not granulo:
            return
        
        info = f"<h3>Dépôt Granulométrique #{granulo_idx + 1}</h3>"
        info += f"<b>Conteneur:</b> {granulo.container_type}<br>"
        info += f"<b>Particules demandées:</b> {granulo.nb_particles}<br>"
        info += f"<b>Particules générées:</b> {len(granulo.generated_ids)}<br>"
        info += f"<b>Rayons:</b> [{granulo.radius_min}, {granulo.radius_max}]<br>"
        info += f"<b>Type d'avatar:</b> {granulo.avatar_type}<br>"
        info += f"<b>Matériau:</b> {granulo.material_name}<br>"
        info += f"<b>Modèle:</b> {granulo.model_name}<br>"
        info += f"<b>Couleur:</b> {granulo.color}<br>"
        if granulo.seed:
            info += f"<b>Seed:</b> {granulo.seed}<br>"
        if granulo.group_name:
            info += f"<b>Groupe:</b> {granulo.group_name}<br>"
        info += "<br><b>Paramètres conteneur:</b><br>"
        for key, value in granulo.container_params.items():
            info += f"  • {key} = {value}<br>"
        
        QMessageBox.information(self, f"Infos: Dépôt #{granulo_idx + 1}", info)
    
    def _clear_form(self):
        """Réinitialise le formulaire"""
        self.nb_input.setText("200")
        self.rmin_input.setText("0.05")
        self.rmax_input.setText("0.15")
        self.seed_input.clear()
        self.color_input.setText("BLUEx")
        self.group_name_input.setText("depot_granulo")
        self.store_check.setChecked(True)
    
    def refresh(self, full_refresh=False):
        """
        Rafraîchit l'affichage de manière optimisée.
        
        Args:
            full_refresh: Si True, rafraîchit aussi les combos (lent)
        """
        # Lire la préférence
        show_individually = getattr(
            getattr(self.controller.state, 'preferences', None),
            'show_granulo_individually', True
        )

        # Si l'affichage individuel est désactivé : forcer + verrouiller le groupe
        if not show_individually:
            self.store_check.setChecked(True)
            self.store_check.setEnabled(False)
            #self.group_required_label.setVisible(True)
        else:
            self.store_check.setEnabled(True)
            #self.group_required_label.setVisible(False)

        # OPTIMISATION : Bloquer tous les signaux et updates pendant refresh
        old_block_tree = self.tree.blockSignals(True)
        old_tree_updates = self.tree.updatesEnabled()
        self.tree.setUpdatesEnabled(False)
        
        try:
            # Rafraîchir le tree (toujours nécessaire)
            self.tree.clear()
            
            granulos = self.controller.state.granulo_generations
            for i, gen in enumerate(granulos):
                nb_generated = len(gen.generated_ids)
                item = QTreeWidgetItem([
                    str(i + 1),
                    gen.container_type,
                    f"{nb_generated}/{gen.nb_particles}",
                    f"[{gen.radius_min:.3f}, {gen.radius_max:.3f}]",
                    gen.group_name or "N/A"
                ])
                item.setData(0, Qt.ItemDataRole.UserRole, i)
                if nb_generated < gen.nb_particles:
                    item.setForeground(2, QBrush(QColor(255, 100, 0)))
                self.tree.addTopLevelItem(item)
            
            # OPTIMISATION : Ne rafraîchir les combos QUE si demandé explicitement
            if full_refresh:
                self.material_combo.blockSignals(True)
                self.model_combo.blockSignals(True)
                self.avatar_combo.blockSignals(True)
                
                self.material_combo.clear()
                materials = self.controller.get_materials()
                self.material_combo.addItems([m.name for m in materials])
                
                self.model_combo.clear()
                models = self.controller.get_models()
                self.model_combo.addItems([m.name for m in models])
                
                self.avatar_combo.clear()
                dim = self.controller.state.dimension
                if dim == 2:
                    avatar_types = ["rigidDisk"]
                else:
                    avatar_types = ["rigidSphere", "rigidCylinder"]
                for avatar_type in avatar_types:
                    self.avatar_combo.addItem(avatar_type, avatar_type)
                
                self.material_combo.blockSignals(False)
                self.model_combo.blockSignals(False)
                self.avatar_combo.blockSignals(False)
        
        finally:
            self.tree.setUpdatesEnabled(old_tree_updates)
            self.tree.blockSignals(old_block_tree)
    
    def closeEvent(self, event):
        """Nettoyage à la fermeture"""
        self.creation_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().closeEvent(event)