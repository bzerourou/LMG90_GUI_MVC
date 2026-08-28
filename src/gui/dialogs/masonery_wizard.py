# ============================================================================
# masonry_wizard.py  —  Assistant de génération de structures maçonnées
# ============================================================================
"""
Wizard Qt6 pour créer des murs en briques avec pylmgc90.

API pylmgc90 utilisée (sources : brick.py, brick_row.py, brick_wall.py) :
  - pre.brick2D(name, lx, ly)           → objet brick2D
  - pre.brick3D(name, lx, ly, lz)       → objet brick3D
      lx = longueur, ly = largeur/profondeur, lz = hauteur
  - brick.rigidBrick(center, model, material, color) → avatar pylmgc90

  - pre.brick_row(brick_ref, disposition, first_brick_type)
      disposition : "paneresse" | "boutisse" | "chant"
      first_brick_type : "1" | "1/2" | "1/4" | "3/4"

  - pre.paneresse_simple(brick_ref, disposition)   → mur simple épaisseur
  - pre.paneresse_double(brick_ref, disposition)   → mur double épaisseur
    Méthodes communes :
      wall.setNumberOfRows(nb)
      wall.setJointThicknessBetweenRows(e)
      wall.computeHeight()
      wall.setFirstRowByNumberOfBricks(first_brick_type, nb_bricks, joint)
      wall.setFirstRowByLength(first_brick_type, length, joint)
      wall.buildRigidWall(origin, model, material, colors)
      wall.buildRigidWallWithoutHalfBricks(origin, model, material, colors)

Modes de génération proposés :
  1. Simple rangée (brick2D / brick3D + rigidBrick) — contrôle total
  2. Mur complet via paneresse_simple — gestion automatique demi-briques

Corrections par rapport à la version précédente :
  - pre.brick2D/brick3D et brick.rigidBrick réutilisés (ils existent bien)
  - Patterns 2D corrigés (Standard, Running Bond, Stack Bond, Flemish Bond)
  - Centers calculés correctement (+ lx/2, + ly/2 depuis le coin)
  - Flemish Bond : brick_lx variable maintenant utilisée dans _place()
  - Running Bond : décalage 1/3 progressif (différent de Standard)
  - AvatarType.EMPTY_AVATAR avec wall_params stockés pour reconstruction
  - maxLength → 8 chars (noms LMGC90)
  - Couleur vide → fallback 'BLUEx'
  - Offset Z pour la 3D
  - validatePage() sur pages critiques
  - state_changed.emit() en fin de génération
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QCheckBox, QMessageBox, QTextEdit, QButtonGroup,
    QHBoxLayout
)
from PyQt6.QtCore import Qt

from ...core.models import (
    Material, Model, Avatar, MaterialType, AvatarType, AvatarOrigin
)
from ...controllers.project_controller import ProjectController


# ── Wizard principal ──────────────────────────────────────────────────────────

class MasonryWizard(QWizard):

    PAGE_INTRO      = 0
    PAGE_DIMENSION  = 1
    PAGE_MATERIAL   = 2
    PAGE_MODEL      = 3
    PAGE_BRICK_DIM  = 4
    PAGE_LAYOUT     = 5
    PAGE_TRANSFORM  = 6
    PAGE_SUMMARY    = 7

    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller

        self.setWindowTitle("🧱 Assistant de Maçonnerie")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(820, 640)

        self.addPage(MasonryIntroPage())
        self.addPage(MasonryDimensionPage())
        self.addPage(MasonryMaterialPage())
        self.addPage(MasonryModelPage())
        self.addPage(BrickDimensionsPage())
        self.addPage(LayoutPage())
        self.addPage(TransformPage())
        self.addPage(MasonrySummaryPage())

        self.setButtonText(QWizard.WizardButton.NextButton,   "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton,   "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Générer")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")

    def accept(self):
        try:
            n = self._generate_masonry()
            QMessageBox.information(
                self, "✅ Succès",
                f"Structure maçonnée générée : {n} brique(s) créée(s)."
            )
            super().accept()
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self, "Erreur de génération",
                f"Génération échouée :\n{e}\n\n{traceback.format_exc()}"
            )

    # ── Génération ────────────────────────────────────────────────────────────
    def _generate_masonry(self) -> int:
        from pylmgc90 import pre

        # ── Dimension ─────────────────────────────────────────────────────────
        dim_page  = self.page(self.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        self.controller.state.dimension = dimension

        # ── Matériau ──────────────────────────────────────────────────────────
        mat_page = self.page(self.PAGE_MATERIAL)
        if mat_page.create_material_check.isChecked():
            mat_name = mat_page.mat_name_input.text().strip()
            if not mat_name:
                raise ValueError("Le nom du matériau ne peut pas être vide.")
            material = Material(
                name=mat_name,
                material_type=MaterialType.RIGID,
                density=mat_page.density_spin.value()
            )
            self.controller.add_material(material)
        else:
            mat_name = mat_page.existing_combo.currentText()
            if not mat_name or mat_name.startswith('('):
                raise ValueError("Aucun matériau sélectionné.")

        # ── Modèle ────────────────────────────────────────────────────────────
        mod_page = self.page(self.PAGE_MODEL)
        if mod_page.create_model_check.isChecked():
            mod_name = mod_page.mod_name_input.text().strip()
            if not mod_name:
                raise ValueError("Le nom du modèle ne peut pas être vide.")
            element = "Rxx2D" if dimension == 2 else "Rxx3D"
            model = Model(
                name=mod_name,
                physics="MECAx",
                element=element,
                dimension=dimension
            )
            self.controller.add_model(model)
        else:
            mod_name = mod_page.existing_combo.currentText()
            if not mod_name or mod_name.startswith('('):
                raise ValueError("Aucun modèle sélectionné.")

        mat_obj = self.controller._pylmgc_materials.get(mat_name)
        mod_obj = self.controller._pylmgc_models.get(mod_name)
        if mat_obj is None:
            raise ValueError(f"Matériau pylmgc90 '{mat_name}' introuvable.")
        if mod_obj is None:
            raise ValueError(f"Modèle pylmgc90 '{mod_name}' introuvable.")

        # ── Dimensions briques ────────────────────────────────────────────────
        dim_brick = self.page(self.PAGE_BRICK_DIM)
        lx        = dim_brick.lx_spin.value()
        ly        = dim_brick.ly_spin.value()
        lz        = dim_brick.lz_spin.value() if dimension == 3 else None
        brick_name = dim_brick.brick_name_input.text().strip() or "std"

        # ── Paramètres d'appareil ─────────────────────────────────────────────
        layout_page  = self.page(self.PAGE_LAYOUT)
        pattern      = layout_page.pattern_combo.currentText()
        nb_rows      = layout_page.rows_spin.value()
        nb_cols      = layout_page.cols_spin.value()
        offset_x     = layout_page.offset_x_spin.value()
        offset_y     = layout_page.offset_y_spin.value()
        offset_z     = layout_page.offset_z_spin.value() if dimension == 3 else 0.0
        joint        = layout_page.joint_spin.value()
        color        = layout_page.color_input.text().strip() or "BLUEx"
        group_name   = (layout_page.group_name_input.text().strip()
                        if layout_page.store_check.isChecked() else None)
        _psm = getattr(layout_page, "pan_size_mode_combo", None)
        pan_use_length = (_psm.currentIndex() == 1) if _psm else False
        _pls = getattr(layout_page, "pan_length_spin", None)
        pan_length     = _pls.value() if _pls else 1.0
        _pnh = getattr(layout_page, "no_half_bricks_check", None)
        pan_no_half    = _pnh.isChecked() if _pnh else False

        # ── Transformations post-génération — lecture défensive ───────────────
        _tf_pg       = self.page(getattr(self, "PAGE_TRANSFORM", -1))
        def _gv(page, attr, default):
            w = getattr(page, attr, None) if page else None
            if w is None: return default
            if hasattr(w, "isChecked"): return w.isChecked()
            if hasattr(w, "value"):     return w.value()
            if hasattr(w, "currentText"): return w.currentText()
            return default
        tf_translate = _gv(_tf_pg, "translate_check", False)
        tf_tx        = _gv(_tf_pg, "tx_spin",         0.0)
        tf_ty        = _gv(_tf_pg, "ty_spin",         0.0)
        tf_tz        = _gv(_tf_pg, "tz_spin",         0.0)
        tf_rotate    = _gv(_tf_pg, "rotate_check",    False)
        tf_cx        = _gv(_tf_pg, "cx_spin",         0.0)
        tf_cy        = _gv(_tf_pg, "cy_spin",         0.0)
        tf_cz        = _gv(_tf_pg, "cz_spin",         0.0)
        tf_axis      = _gv(_tf_pg, "axis_combo",      "Z")
        tf_alpha_deg = _gv(_tf_pg, "alpha_spin",      0.0)
        tf_copy      = _gv(_tf_pg, "copy_check",      False)
        tf_copy_dx   = _gv(_tf_pg, "copy_dx_spin",    0.0)
        tf_copy_dy   = _gv(_tf_pg, "copy_dy_spin",    0.0)
        tf_copy_dz   = _gv(_tf_pg, "copy_dz_spin",    0.0)

        # ── Mode rapide (batch) — case à cocher LayoutPage ─────────────────────
        # Regroupe toute la génération dans self.controller._batch_mode :
        # un seul state_changed.emit() à la fin au lieu d'un potentiel signal
        # par brique. Purement une optimisation de flux de signaux ; la
        # géométrie et les objets pylmgc90 créés sont IDENTIQUES au mode
        # normal (contrairement au SoA granulo/for-loop, qui produit une
        # structure de données différente). Ce n'est donc pas un
        # ParticlePopulation — les briques restent des Avatar individuels,
        # pleinement éditables un par un après génération.
        fast_mode = getattr(layout_page, "fast_mode_check", None)
        use_fast_mode = fast_mode.isChecked() if fast_mode else False

        was_batch = self.controller._batch_mode
        if use_fast_mode:
            self.controller._batch_mode = True

        try:
            # ── Création de la brique de référence pylmgc90 ───────────────────────
            if dimension == 2:
                brick_ref = pre.brick2D(brick_name, lx, ly)
            else:
                brick_ref = pre.brick3D(brick_name, lx, ly, lz)

            # ── Génération selon le pattern ───────────────────────────────────────
            generated_indices = []

            def _place_body(body, center, bx, by, bz=None):
                """Enregistre le body pylmgc90 et l'Avatar correspondant."""
                self.controller._bodies_container.addAvatar(body)
                self.controller._pylmgc_bodies.append(body)
                wp = {'l': bx, 'h': by, 'brick_name': brick_name}
                if bz is not None:
                    wp['lz'] = bz
                av = Avatar(
                    avatar_type=AvatarType.EMPTY_AVATAR,
                    center=list(center),
                    material_name=mat_name,
                    model_name=mod_name,
                    color=color,
                    origin=AvatarOrigin.MANUAL,
                    wall_params=wp,
                    contactors=[]
                )
                self.controller.state.avatars.append(av)
                generated_indices.append(len(self.controller.state.avatars) - 1)

            def _place(cx, cy, bx, by):
                """Crée et place une brique via brick2D/3D.rigidBrick."""
                center = [cx, cy] if dimension == 2 else [cx, cy, offset_z]
                if dimension == 2:
                    b = pre.brick2D(brick_name, bx, by)
                else:
                    b = pre.brick3D(brick_name, bx, by, lz)
                body = b.rigidBrick(
                    center=center, model=mod_obj, material=mat_obj, color=color
                )
                _place_body(body, center, bx, by, lz)

            # ── Standard : décalage demi-brique sur rangs impairs ─────────────────
            if pattern == "Standard":
                for row in range(nb_rows):
                    row_offset = (lx / 2.0) if (row % 2 == 1) else 0.0
                    for col in range(nb_cols):
                        cx = offset_x + col * (lx + joint) + row_offset + lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, lx, ly)

            # ── Running Bond : décalage progressif d'un tiers par rang ────────────
            elif pattern == "Running Bond":
                for row in range(nb_rows):
                    row_offset = (row % 3) * (lx / 3.0)
                    for col in range(nb_cols):
                        cx = offset_x + col * (lx + joint) + row_offset + lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, lx, ly)

            # ── Stack Bond : joints parfaitement alignés ───────────────────────────
            elif pattern == "Stack Bond":
                for row in range(nb_rows):
                    for col in range(nb_cols):
                        cx = offset_x + col * (lx + joint) + lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, lx, ly)

            # ── Flemish Bond : alternance panneresse (lx) / boutisse (lx/2) ───────
            elif pattern == "Flemish Bond":
                for row in range(nb_rows):
                    x_cursor = offset_x
                    for col in range(nb_cols):
                        if (row + col) % 2 == 0:
                            brick_lx = lx
                        else:
                            brick_lx = lx / 2.0
                        cx = x_cursor + brick_lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, brick_lx, ly)
                        x_cursor += brick_lx + joint

            # ── Paneresse simple / double (API pylmgc90 brick_wall) ───────────────
            elif pattern in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)"):
                disposition = layout_page.disposition_combo.currentText()
                first_type  = layout_page.first_brick_combo.currentText()

                if dimension == 2:
                    brick_ref_wall = pre.brick3D(brick_name, lx, 1.0, ly)
                else:
                    brick_ref_wall = pre.brick3D(brick_name, lx, ly, lz)

                if "double" in pattern:
                    wall = pre.paneresse_double(brick_ref=brick_ref_wall, disposition=disposition)
                else:
                    wall = pre.paneresse_simple(brick_ref=brick_ref_wall, disposition=disposition)

                wall.setNumberOfRows(nb_rows)
                wall.setJointThicknessBetweenRows(joint)
                wall.computeHeight()

                if pan_use_length:
                    wall.setFirstRowByLength(
                        first_brick_type=first_type,
                        length=pan_length,
                        joint_thickness=joint
                    )
                else:
                    wall.setFirstRowByNumberOfBricks(
                        first_brick_type=first_type,
                        nb_bricks=nb_cols,
                        joint_thickness=joint
                    )

                origin = [offset_x, offset_y, offset_z] if dimension == 3 \
                         else [offset_x, offset_y, 0.0]

                if pan_no_half:
                    bodies_container = wall.buildRigidWallWithoutHalfBricks(
                        origin=origin,
                        model=mod_obj,
                        material=mat_obj,
                        colors=[color, color]
                    )
                else:
                    bodies_container = wall.buildRigidWall(
                        origin=origin,
                        model=mod_obj,
                        material=mat_obj,
                        colors=[color, color]
                    )

                for body in bodies_container:
                    center = list(body.nodes[1].coor)
                    _place_body(body, center, lx, ly, lz)

            else:
                raise ValueError(f"Appareil inconnu : '{pattern}'")

            # ── Transformations post-génération ──────────────────────────────────
            if tf_translate or tf_rotate or tf_copy:
                import math as _math, copy as _copy, numpy as _np
                from ...core.models import DOFOperation

                generated_ids = [
                    self.controller.state.avatars[idx].avatar_id for idx in generated_indices
                ]

                if tf_translate :
                    for aid in generated_indices :
                        params = {'dx': tf_tx, 'dy': tf_ty}
                        if dimension == 3:
                            params['dz'] = tf_tz
                        self.controller.add_dof_operation(
                            DOFOperation(
                                target_type='avatar',
                                target_value=aid,
                                operation='translate',
                                params=params
                            )
                        )
                if tf_rotate :
                    _alpha = _math.radians(tf_alpha_deg)
                    _ax = {'X': [1.,0.,0.], 'Y': [0.,1.,0.], 'Z': [0.,0.,1.]}[tf_axis]
                    if dimension == 3:
                        _ctr = [tf_cx, tf_cy, tf_cz]
                    else:
                        _ctr = [tf_cx, tf_cy]
                    for aid in generated_indices:
                        self.controller.add_dof_operation(
                            DOFOperation(
                                target_type='avatar',
                                target_value=aid,
                                operation='rotate',
                                params={
                                    'description': 'axis',
                                    'center': _ctr, 
                                    'axis': _ax, 
                                    'alpha': _alpha}
                            )
                        )

                if tf_copy:
                    session_bodies = self.controller._pylmgc_bodies[-len(generated_indices):]
                    copy_bodies = _copy.deepcopy(session_bodies)
                    for b in copy_bodies:
                        if dimension == 3:
                            b.translate(dx=tf_copy_dx, dy=tf_copy_dy, dz=tf_copy_dz)
                        else:
                            b.translate(dx=tf_copy_dx, dy=tf_copy_dy)
                    for b in copy_bodies:
                        self.controller._bodies_container.addAvatar(b)
                        self.controller._pylmgc_bodies.append(b)
                        try:
                            center_copy = list(b.nodes[1].coor)
                        except Exception:
                            center_copy = [0., 0., 0.]
                        self.controller.state.avatars.append(Avatar(
                            avatar_type=AvatarType.EMPTY_AVATAR,
                            center=center_copy,
                            material_name=mat_name,
                            model_name=mod_name,
                            color=color,
                            origin=AvatarOrigin.MANUAL,
                            wall_params={'l': lx, 'h': ly,
                                        'brick_name': brick_name, 'copy': True},
                            contactors=[]
                        ))
                        generated_indices.append(len(self.controller.state.avatars) - 1)

            # ── Groupe ────────────────────────────────────────────────────────────
            if group_name and generated_indices:
                if not hasattr(self.controller.state, 'avatar_groups'):
                    self.controller.state.avatar_groups = {}
                if group_name not in self.controller.state.avatar_groups:
                    self.controller.state.avatar_groups[group_name] = []

                generated_avatar_ids = [
                    self.controller.state.avatars[idx].avatar_id
                    for idx in generated_indices
                    if idx < len(self.controller.state.avatars)
                ]
                self.controller.state.avatar_groups[group_name].extend(generated_avatar_ids)

                if not hasattr(self.controller.state, 'masonry_patterns'):
                    self.controller.state.masonry_patterns = {}
                mp = {
                    'pattern':   pattern,
                    'lx':        lx,
                    'ly':        ly,
                    'lz':        lz,
                    'nb_rows':   nb_rows,
                    'nb_cols':   nb_cols,
                    'offset_x':  offset_x,
                    'offset_y':  offset_y,
                    'offset_z':  offset_z,
                    'joint':     joint,
                    'brick_name': brick_name,
                    'mat':       mat_name,
                    'mod':       mod_name,
                    'color':     color,
                    'dim':       dimension,
                }
                if pattern in ('Paneresse simple (pylmgc90)', 'Paneresse double (pylmgc90)'):
                    mp['disposition']    = layout_page.disposition_combo.currentText()
                    mp['first_type']     = layout_page.first_brick_combo.currentText()
                    mp['pan_use_length'] = pan_use_length
                    mp['pan_length']     = pan_length
                    mp['pan_no_half']    = pan_no_half
                mp['tf_translate']  = tf_translate
                mp['tf_tx']         = tf_tx
                mp['tf_ty']         = tf_ty
                mp['tf_tz']         = tf_tz
                mp['tf_rotate']     = tf_rotate
                mp['tf_cx']         = tf_cx
                mp['tf_cy']         = tf_cy
                mp['tf_cz']         = tf_cz
                mp['tf_axis']       = tf_axis
                mp['tf_alpha_deg']  = tf_alpha_deg
                mp['tf_copy']       = tf_copy
                mp['tf_copy_dx']    = tf_copy_dx
                mp['tf_copy_dy']    = tf_copy_dy
                mp['tf_copy_dz']    = tf_copy_dz
                self.controller.state.masonry_patterns[group_name] = mp

        finally:
            # Restaurer l'état précédent de _batch_mode (défensif si ce
            # wizard était lui-même appelé depuis un contexte déjà batché)
            self.controller._batch_mode = was_batch

        # Un seul signal, que le mode rapide ait été utilisé ou non
        self.controller.state_changed.emit()
        return len(generated_indices)

# ── Pages ─────────────────────────────────────────────────────────────────────

class MasonryIntroPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Assistant de Maçonnerie")
        self.setSubTitle(
            "Créez des structures maçonnées via l'API pylmgc90 (brick2D / brick3D)."
        )
        layout = QVBoxLayout(self)
        intro  = QLabel(
            "<h3>📋 Étapes :</h3>"
            "<ol>"
            "<li>✅Choisir la dimension (2D ou 3D)</li>"
            "<li>✅Définir le matériau des briques</li>"
            "<li>✅Définir le modèle physique</li>"
            "<li>✅Configurer les dimensions de la brique</li>"
            "<li>✅Choisir l'appareil et les paramètres du mur</li>"
            "<li>✅Vérifier le récapitulatif et générer</li>"
            "</ol>"
            "<p><b>Appareils disponibles :</b><br>"
            "• Standard (décalage ½ brique)<br>"
            "• Running Bond (décalage ⅓ progressif)<br>"
            "• Stack Bond (joints alignés)<br>"
            "• Flemish Bond (panneresse/boutisse alternées)<br>"
            "• Paneresse simple — <code>pre.paneresse_simple</code> (mur simple épaisseur)<br>"
            "• Paneresse double — <code>pre.paneresse_double</code> (mur double épaisseur)</p>"
            "<p><b>💡 info : API utilisée :</b> <code>pre.brick2D(name, lx, ly)</code>, "
            "<code>pre.brick3D(name, lx, ly, lz)</code>, "
            "<code>brick.rigidBrick(center, model, material, color)</code></p>"
            "<p><i>⏱️ Temps estimé : 2-3 minutes</i></p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addStretch()


class MasonryDimensionPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("📐 Dimension")
        self.setSubTitle("Choisissez la dimension de votre structure.")

        layout     = QVBoxLayout(self)
        dim_group  = QGroupBox("Dimension spatiale")
        dim_layout = QVBoxLayout()

        self.dim_2d_radio = QRadioButton("2D — Structure plane (brick2D)")
        self.dim_2d_radio.setChecked(True)
        dim_layout.addWidget(self.dim_2d_radio)
        info_2d = QLabel("    💡 Murs plans, sections 2D")
        info_2d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_2d)

        dim_layout.addSpacing(12)

        self.dim_3d_radio = QRadioButton("3D — Structure volumique (brick3D)")
        dim_layout.addWidget(self.dim_3d_radio)
        info_3d = QLabel("    💡 Murs 3D, voûtes — lx=longueur, ly=profondeur, lz=hauteur")
        info_3d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_3d)

        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        layout.addStretch()



class MasonryMaterialPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Matériau des Briques")
        self.setSubTitle("Créez un nouveau matériau ou utilisez un existant.")

        layout = QVBoxLayout(self)

        choice_group  = QGroupBox("Source du matériau")
        choice_layout = QVBoxLayout()
        self.create_material_check = QCheckBox("Créer un nouveau matériau")
        self.create_material_check.setChecked(True)
        self.create_material_check.toggled.connect(self._toggle_mode)
        choice_layout.addWidget(self.create_material_check)
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)

        self.new_material_group = QGroupBox("Nouveau matériau")
        new_form = QFormLayout()
        self.mat_name_input = QLineEdit("brick")
        self.mat_name_input.setMaxLength(8)
        self.mat_name_input.setPlaceholderText("Ex: brick, macon, stone")
        new_form.addRow("Nom (=5 car. ) :", self.mat_name_input)
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(100, 20000)
        self.density_spin.setValue(1800)
        self.density_spin.setSuffix(" kg/m³")
        new_form.addRow("Densité :", self.density_spin)
        self.new_material_group.setLayout(new_form)
        layout.addWidget(self.new_material_group)

        self.existing_material_group = QGroupBox("Matériau existant")
        existing_form = QFormLayout()
        self.existing_combo = QComboBox()
        existing_form.addRow("Sélectionner :", self.existing_combo)
        self.existing_material_group.setLayout(existing_form)
        self.existing_material_group.setVisible(False)
        layout.addWidget(self.existing_material_group)
        layout.addStretch()

    def _toggle_mode(self, create_new: bool):
        self.new_material_group.setVisible(create_new)
        self.existing_material_group.setVisible(not create_new)

    def initializePage(self):
        materials = self.wizard().controller.get_materials()
        self.existing_combo.clear()
        if materials:
            self.existing_combo.addItems([m.name for m in materials])
        else:
            self.existing_combo.addItem("(Aucun matériau disponible)")

    def validatePage(self) -> bool:
        if self.create_material_check.isChecked():
            if not self.mat_name_input.text().strip():
                QMessageBox.warning(self, "Nom requis",
                                    "Entrez un nom pour le matériau.")
                return False
        else:
            if self.existing_combo.currentText().startswith('('):
                QMessageBox.warning(self, "Matériau requis",
                                    "Aucun matériau disponible.")
                return False
        return True


class MasonryModelPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("⚙️ Modèle Physique")
        self.setSubTitle("Créez un nouveau modèle ou utilisez un existant.")

        layout = QVBoxLayout(self)

        choice_group  = QGroupBox("Source du modèle")
        choice_layout = QVBoxLayout()
        self.create_model_check = QCheckBox("Créer un nouveau modèle")
        self.create_model_check.setChecked(True)
        self.create_model_check.toggled.connect(self._toggle_mode)
        choice_layout.addWidget(self.create_model_check)
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)

        self.new_model_group = QGroupBox("Nouveau modèle")
        new_form = QFormLayout()
        self.mod_name_input = QLineEdit("rigid")
        self.mod_name_input.setMaxLength(8)
        self.mod_name_input.setPlaceholderText("Ex: rigid, model")
        new_form.addRow("Nom (=5 car.) :", self.mod_name_input)
        info = QLabel("💡 physics=MECAx, element=Rxx2D (2D) ou Rxx3D (3D).")
        info.setStyleSheet("color: gray; font-size: 9pt;")
        new_form.addRow("", info)
        self.new_model_group.setLayout(new_form)
        layout.addWidget(self.new_model_group)

        self.existing_model_group = QGroupBox("Modèle existant")
        existing_form = QFormLayout()
        self.existing_combo = QComboBox()
        existing_form.addRow("Sélectionner :", self.existing_combo)
        self.existing_model_group.setLayout(existing_form)
        self.existing_model_group.setVisible(False)
        layout.addWidget(self.existing_model_group)
        layout.addStretch()

    def _toggle_mode(self, create_new: bool):
        self.new_model_group.setVisible(create_new)
        self.existing_model_group.setVisible(not create_new)

    def initializePage(self):
        models = self.wizard().controller.get_models()
        self.existing_combo.clear()
        if models:
            self.existing_combo.addItems([m.name for m in models])
        else:
            self.existing_combo.addItem("(Aucun modèle disponible)")

    def validatePage(self) -> bool:
        if self.create_model_check.isChecked():
            if not self.mod_name_input.text().strip():
                QMessageBox.warning(self, "Nom requis",
                                    "Entrez un nom pour le modèle.")
                return False
        else:
            if self.existing_combo.currentText().startswith('('):
                QMessageBox.warning(self, "Modèle requis",
                                    "Aucun modèle disponible.")
                return False
        return True


class BrickDimensionsPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("📏 Dimensions de la Brique")
        self.setSubTitle(
            "Définissez les dimensions passées à brick2D(name, lx, ly) "
            "ou brick3D(name, lx, ly, lz)."
        )

        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.brick_name_input = QLineEdit("std")
        self.brick_name_input.setMaxLength(8)
        self.brick_name_input.setPlaceholderText("std, half, custom…")
        form.addRow("Nom brique :", self.brick_name_input)

        self.lx_spin = QDoubleSpinBox()
        self.lx_spin.setRange(0.001, 10.0)
        self.lx_spin.setValue(0.20)
        self.lx_spin.setSuffix(" m")
        self.lx_spin.setDecimals(3)
        form.addRow("lx — longueur :", self.lx_spin)

        self.ly_spin = QDoubleSpinBox()
        self.ly_spin.setRange(0.001, 10.0)
        self.ly_spin.setValue(0.065)
        self.ly_spin.setSuffix(" m")
        self.ly_spin.setDecimals(3)
        # Le label ly change selon la dimension (hauteur 2D / profondeur 3D)
        self.ly_label = QLabel("ly — hauteur (2D) :")
        form.addRow(self.ly_label, self.ly_spin)

        self.lz_label = QLabel("lz — hauteur (3D) :")
        self.lz_spin  = QDoubleSpinBox()
        self.lz_spin.setRange(0.001, 10.0)
        self.lz_spin.setValue(0.065)
        self.lz_spin.setSuffix(" m")
        self.lz_spin.setDecimals(3)
        form.addRow(self.lz_label, self.lz_spin)

        info = QLabel(
            "💡 Brique standard française : lx=0.20 m, lz=0.065 m, ly=0.10 m<br>"
            "En 2D : brick2D(name, lx, ly) — ly est la hauteur<br>"
            "En 3D : brick3D(name, lx, ly, lz) — ly est la profondeur, lz la hauteur"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 9pt;")
        form.addRow("", info)

        layout.addLayout(form)
        layout.addStretch()


    def initializePage(self):
        wizard    = self.wizard()
        dim_page  = wizard.page(MasonryWizard.PAGE_DIMENSION)
        is3d      = dim_page.dim_3d_radio.isChecked()
        # Afficher lz seulement en 3D
        self.lz_label.setVisible(is3d)
        self.lz_spin.setVisible(is3d)
        # Adapter le label ly
        if is3d:
            self.ly_label.setText("ly — profondeur (3D) :")
            self.ly_spin.setValue(0.10)
        else:
            self.ly_label.setText("ly — hauteur (2D) :")
            self.ly_spin.setValue(0.065)


class LayoutPage(QWizardPage):

    _PATTERN_INFO = {
        "Standard":
            "Décalage d'une demi-brique (lx/2) entre rangs consécutifs.",
        "Running Bond":
            "Décalage progressif d'un tiers de brique (lx/3) par rang : "
            "rang 0 → 0, rang 1 → lx/3, rang 2 → 2lx/3, rang 3 → 0…",
        "Stack Bond":
            "Joints verticaux parfaitement alignés — esthétique mais "
            "mécaniquement moins résistant.",
        "Flemish Bond":
            "Alternance panneresse (lx) / boutisse (lx/2) dans chaque rang.",
        "Paneresse simple (pylmgc90)":
            "pre.paneresse_simple — mur simple épaisseur. "
            "Gestion automatique des demi-briques. "
            "Disposition, type de première brique et mode de dimensionnement configurables.",
        "Paneresse double (pylmgc90)":
            "pre.paneresse_double — mur double épaisseur (deux rangées de briques). "
            "Mêmes options que la paneresse simple.",
    }

    def __init__(self):
        super().__init__()
        self.setTitle("🏗️ Appareil de Maçonnerie")
        self.setSubTitle("Configurez la disposition des briques.")

        layout = QVBoxLayout(self)

        # Type d'appareil
        pattern_group = QGroupBox("Type d'appareil")
        pattern_form  = QFormLayout()
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(list(self._PATTERN_INFO.keys()))
        self.pattern_combo.currentTextChanged.connect(self._on_pattern_changed)
        pattern_form.addRow("Appareil :", self.pattern_combo)
        pattern_group.setLayout(pattern_form)
        layout.addWidget(pattern_group)

        self.pattern_info = QLabel()
        self.pattern_info.setWordWrap(True)
        self.pattern_info.setStyleSheet(
            "background-color: #f0f0f0; padding: 8px; border-radius: 5px;"
        )
        layout.addWidget(self.pattern_info)

        # Options paneresse_simple / paneresse_double (cachées par défaut)
        self.paneresse_group = QGroupBox("Options paneresse (pylmgc90)")
        pan_form = QFormLayout()

        self.disposition_combo = QComboBox()
        self.disposition_combo.addItems(["paneresse", "boutisse", "chant"])
        self.disposition_combo.setToolTip(
            "paneresse : briques posées dans le sens de la longueur\n"
            "boutisse  : briques posées en travers (face visible = petit côté)\n"
            "chant     : briques posées sur chant (hauteur = largeur brique)"
        )
        pan_form.addRow("Disposition :", self.disposition_combo)

        self.first_brick_combo = QComboBox()
        self.first_brick_combo.addItems(["1", "1/2", "1/4", "3/4"])
        self.first_brick_combo.setToolTip(
            "Type de la première brique du premier rang.\n"
            "1=brique entière, 1/2=demi-brique, 1/4 ou 3/4=quart/trois-quarts."
        )
        pan_form.addRow("Première brique :", self.first_brick_combo)

        # Mode dimensionnement : nb colonnes OU longueur totale
        self.pan_size_mode_combo = QComboBox()
        self.pan_size_mode_combo.addItems(["Nombre de briques", "Longueur totale (m)"])
        self.pan_size_mode_combo.currentIndexChanged.connect(self._on_pan_size_mode_changed)
        self.pan_size_mode_combo.setToolTip(
            "Nombre de briques : setFirstRowByNumberOfBricks(type, nb, joint)\n"
            "Longueur totale   : setFirstRowByLength(type, longueur, joint)"
        )
        pan_form.addRow("Dimensionnement :", self.pan_size_mode_combo)

        self.pan_length_label = QLabel("Longueur totale :")
        self.pan_length_spin  = QDoubleSpinBox()
        self.pan_length_spin.setRange(0.01, 100.0)
        self.pan_length_spin.setValue(3.0)
        self.pan_length_spin.setSuffix(" m")
        self.pan_length_spin.setDecimals(3)
        self.pan_length_spin.setVisible(False)
        self.pan_length_label.setVisible(False)
        pan_form.addRow(self.pan_length_label, self.pan_length_spin)

        self.no_half_bricks_check = QCheckBox("Sans demi-briques (buildRigidWallWithoutHalfBricks)")
        self.no_half_bricks_check.setToolTip(
            "Utilise buildRigidWallWithoutHalfBricks au lieu de buildRigidWall.\n"
            "Le mur est généré sans découpe de briques aux extrémités."
        )
        pan_form.addRow(self.no_half_bricks_check)

        self.paneresse_group.setLayout(pan_form)
        self.paneresse_group.setVisible(False)
        layout.addWidget(self.paneresse_group)

        # Dimensions du mur
        dim_group = QGroupBox("Dimensions du mur")
        dim_form  = QFormLayout()

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 200)
        self.rows_spin.setValue(10)
        dim_form.addRow("Nombre de rangs :", self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 200)
        self.cols_spin.setValue(15)
        dim_form.addRow("Nombre de colonnes :", self.cols_spin)

        self.joint_spin = QDoubleSpinBox()
        self.joint_spin.setRange(0.0, 0.05)
        self.joint_spin.setValue(0.010)
        self.joint_spin.setSuffix(" m")
        self.joint_spin.setSingleStep(0.001)
        self.joint_spin.setDecimals(3)
        dim_form.addRow("Épaisseur joint :", self.joint_spin)

        dim_group.setLayout(dim_form)
        layout.addWidget(dim_group)

        # Position initiale
        pos_group = QGroupBox("Position initiale (coin inférieur gauche)")
        pos_form  = QFormLayout()

        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-1000.0, 1000.0)
        self.offset_x_spin.setValue(0.0)
        self.offset_x_spin.setSuffix(" m")
        self.offset_x_spin.setDecimals(3)
        pos_form.addRow("Offset X :", self.offset_x_spin)

        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-1000.0, 1000.0)
        self.offset_y_spin.setValue(0.0)
        self.offset_y_spin.setSuffix(" m")
        self.offset_y_spin.setDecimals(3)
        pos_form.addRow("Offset Y :", self.offset_y_spin)

        self.offset_z_label = QLabel("Offset Z :")
        self.offset_z_spin  = QDoubleSpinBox()
        self.offset_z_spin.setRange(-1000.0, 1000.0)
        self.offset_z_spin.setValue(0.0)
        self.offset_z_spin.setSuffix(" m")
        self.offset_z_spin.setDecimals(3)
        pos_form.addRow(self.offset_z_label, self.offset_z_spin)

        pos_group.setLayout(pos_form)
        layout.addWidget(pos_group)

# ── Options ───────────────────────────────────────────────────────────
        opt_group = QGroupBox("Options")
        opt_form  = QFormLayout()

        self.color_input = QLineEdit("BLUEx")
        self.color_input.setPlaceholderText("BLUEx, REDxx, VERTx, GRAYx…")
        opt_form.addRow("Couleur LMGC90 :", self.color_input)

        self.store_check      = QCheckBox("Stocker dans un groupe")
        self.store_check.setChecked(True)
        self.group_name_input = QLineEdit("mur_briques")
        opt_form.addRow(self.store_check, self.group_name_input)

        self.fast_mode_check = QCheckBox("Mode rapide (regroupe les signaux — recommandé au-delà de ~500 briques)")
        self.fast_mode_check.setToolTip(
            "Regroupe toute la génération dans un seul rafraîchissement UI\n"
            "au lieu d'un potentiel signal par brique. La géométrie produite\n"
            "est identique au mode normal — chaque brique reste un Avatar\n"
            "individuel, éditable après génération. Recommandé pour les murs\n"
            "de grande taille (nombreux rangs × colonnes)."
        )
        self.fast_mode_check.setChecked(False)
        opt_form.addRow("", self.fast_mode_check)

        opt_group.setLayout(opt_form)
        layout.addWidget(opt_group)

        layout.addStretch()
        self._on_pattern_changed("Standard")

    def initializePage(self):
        dim_page  = self.wizard().page(MasonryWizard.PAGE_DIMENSION)
        is3d      = dim_page.dim_3d_radio.isChecked()
        self.offset_z_label.setVisible(is3d)
        self.offset_z_spin.setVisible(is3d)
        # Paneresse simple et double seulement pour la 3d

        for item in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)"):
            idx = self.pattern_combo.findText(item)
            if idx >= 0:
                self.pattern_combo.model().item(idx).setEnabled(is3d)

    def _on_pan_size_mode_changed(self, idx: int):
        use_length = (idx == 1)
        self.pan_length_label.setVisible(use_length)
        self.pan_length_spin.setVisible(use_length)

    def _on_pattern_changed(self, pattern: str):
        self.pattern_info.setText(self._PATTERN_INFO.get(pattern, ""))
        is_pan = pattern in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)")
        self.paneresse_group.setVisible(is_pan)
        if is_pan:
            self.paneresse_group.setTitle(
                "Options paneresse simple" if "simple" in pattern
                else "Options paneresse double"
            )

    def validatePage(self) -> bool:
        total = self.rows_spin.value() * self.cols_spin.value()
        if total > 5000:
            reply = QMessageBox.question(
                self, "⚠️ Attention",
                f"Vous allez créer environ {total} briques.\n"
                "La génération peut prendre plusieurs secondes. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        return True


class TransformPage(QWizardPage):
    """Page de configuration des transformations post-génération."""

    def __init__(self):
        super().__init__()
        self.setTitle("🔄 Transformations")
        self.setSubTitle(
            "Appliquez des transformations au mur après génération : "
            "translation, rotation, copie décalée."
        )

        layout = QVBoxLayout(self)

        # ── Note explicative ─────────────────────────────────────────────────
        note = QLabel(
            "💡 Ces transformations s'appliquent sur le <code>bodies_container</code> "
            "pylmgc90 après <code>buildRigidWall()</code>.<br>"
            "Elles correspondent à : <code>bodies.translate()</code>, "
            "<code>bodies.rotate()</code> et <code>copy.deepcopy(bodies)</code>."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background:#e8f4fd; padding:8px; border-radius:4px; font-size:9pt;"
        )
        layout.addWidget(note)

        # ── Translation ───────────────────────────────────────────────────────
        grp_tr = QGroupBox("Translation  —  bodies.translate(dx, dy, dz)")
        tr_form = QFormLayout()

        self.translate_check = QCheckBox("Activer la translation")
        self.translate_check.setChecked(False)
        self.translate_check.toggled.connect(self._on_translate_toggled)
        tr_form.addRow(self.translate_check)

        self.tx_spin = QDoubleSpinBox()
        self.tx_spin.setRange(-1000., 1000.)
        self.tx_spin.setValue(0.)
        self.tx_spin.setSuffix(" m")
        self.tx_spin.setDecimals(4)
        self.tx_spin.setEnabled(False)
        tr_form.addRow("dx :", self.tx_spin)

        self.ty_spin = QDoubleSpinBox()
        self.ty_spin.setRange(-1000., 1000.)
        self.ty_spin.setValue(0.)
        self.ty_spin.setSuffix(" m")
        self.ty_spin.setDecimals(4)
        self.ty_spin.setEnabled(False)
        tr_form.addRow("dy :", self.ty_spin)

        self.tz_label = QLabel("dz :")
        self.tz_spin  = QDoubleSpinBox()
        self.tz_spin.setRange(-1000., 1000.)
        self.tz_spin.setValue(0.)
        self.tz_spin.setSuffix(" m")
        self.tz_spin.setDecimals(4)
        self.tz_spin.setEnabled(False)
        tr_form.addRow(self.tz_label, self.tz_spin)
        grp_tr.setLayout(tr_form)
        layout.addWidget(grp_tr)

        # ── Rotation ─────────────────────────────────────────────────────────
        grp_rot = QGroupBox(
            "Rotation  —  bodies.rotate(description='axis', center, axis, alpha)"
        )
        rot_form = QFormLayout()

        self.rotate_check = QCheckBox("Activer la rotation")
        self.rotate_check.setChecked(False)
        self.rotate_check.toggled.connect(self._on_rotate_toggled)
        rot_form.addRow(self.rotate_check)

        self.cx_spin = QDoubleSpinBox()
        self.cx_spin.setRange(-1000., 1000.)
        self.cx_spin.setValue(0.)
        self.cx_spin.setSuffix(" m")
        self.cx_spin.setDecimals(4)
        self.cx_spin.setEnabled(False)
        rot_form.addRow("Centre x :", self.cx_spin)

        self.cy_spin = QDoubleSpinBox()
        self.cy_spin.setRange(-1000., 1000.)
        self.cy_spin.setValue(0.)
        self.cy_spin.setSuffix(" m")
        self.cy_spin.setDecimals(4)
        self.cy_spin.setEnabled(False)
        rot_form.addRow("Centre y :", self.cy_spin)

        self.cz_spin = QDoubleSpinBox()
        self.cz_spin.setRange(-1000., 1000.)
        self.cz_spin.setValue(0.)
        self.cz_spin.setSuffix(" m")
        self.cz_spin.setDecimals(4)
        self.cz_spin.setEnabled(False)
        rot_form.addRow("Centre z :", self.cz_spin)

        self.axis_combo = QComboBox()

        self.axis_combo.setToolTip(
            "Axe de rotation.\n"
            "Z = rotation dans le plan XY (90° pour angle droit)\n"
        )
        self.axis_combo.setEnabled(False)
        rot_form.addRow("Axe :", self.axis_combo)

        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(-360., 360.)
        self.alpha_spin.setValue(90.)
        self.alpha_spin.setSuffix(" °")
        self.alpha_spin.setDecimals(2)
        self.alpha_spin.setToolTip(
            "Angle de rotation en degrés.\n"
            "90° = angle droit, 180° = demi-tour.\n"
            "Converti en radians pour l'API pylmgc90."
        )
        self.alpha_spin.setEnabled(False)
        rot_form.addRow("Angle α :", self.alpha_spin)

        grp_rot.setLayout(rot_form)
        layout.addWidget(grp_rot)

        # ── Copie décalée ─────────────────────────────────────────────────────
        grp_copy = QGroupBox(
            "Copie décalée  —  copy.deepcopy(bodies) + translate"
        )
        copy_form = QFormLayout()

        self.copy_check = QCheckBox("Créer une copie décalée du mur")
        self.copy_check.setChecked(False)
        self.copy_check.toggled.connect(self._on_copy_toggled)
        self.copy_check.setToolTip(
            "Duplique le mur généré (deepcopy) puis lui applique\n"
            "un décalage. Utile pour créer deux murs parallèles\n"
            "ou fermer un angle (avec la rotation active)."
        )
        copy_form.addRow(self.copy_check)

        self.copy_dx_spin = QDoubleSpinBox()
        self.copy_dx_spin.setRange(-1000., 1000.)
        self.copy_dx_spin.setValue(0.)
        self.copy_dx_spin.setSuffix(" m")
        self.copy_dx_spin.setDecimals(4)
        self.copy_dx_spin.setEnabled(False)
        copy_form.addRow("Décalage dx :", self.copy_dx_spin)

        self.copy_dy_spin = QDoubleSpinBox()
        self.copy_dy_spin.setRange(-1000., 1000.)
        self.copy_dy_spin.setValue(0.)
        self.copy_dy_spin.setSuffix(" m")
        self.copy_dy_spin.setDecimals(4)
        self.copy_dy_spin.setEnabled(False)
        copy_form.addRow("Décalage dy :", self.copy_dy_spin)

        self.copy_dz_label = QLabel("Décalage dz :")
        self.copy_dz_spin  = QDoubleSpinBox()
        self.copy_dz_spin.setRange(-1000., 1000.)
        self.copy_dz_spin.setValue(0.)
        self.copy_dz_spin.setSuffix(" m")
        self.copy_dz_spin.setDecimals(4)
        self.copy_dz_spin.setEnabled(False)
        copy_form.addRow(self.copy_dz_label, self.copy_dz_spin)

        grp_copy.setLayout(copy_form)
        layout.addWidget(grp_copy)

        layout.addStretch()

    # ── Helpers enable/disable ────────────────────────────────────────────────
    def _on_translate_toggled(self, v: bool):
        for w in (self.tx_spin, self.ty_spin, self.tz_spin):
            w.setEnabled(v)

    def _on_rotate_toggled(self, v: bool):
        is3d = self.wizard().page(
            MasonryWizard.PAGE_DIMENSION
        ).dim_3d_radio.isChecked()

        self.cx_spin.setEnabled(v)
        self.cy_spin.setEnabled(v)
        self.alpha_spin.setEnabled(v)
        if is3d:
            self.cz_spin.setEnabled(v)
            self.axis_combo.setEnabled(v)
        else:
            self.cz_spin.setEnabled(False)
            self.axis_combo.setEnabled(v)


    def _on_copy_toggled(self, v: bool):
        for w in (self.copy_dx_spin, self.copy_dy_spin, self.copy_dz_spin):
            w.setEnabled(v)

    def _update_axis_options(self, is3d: bool):
        self.axis_combo.clear()
        if is3d:
            self.axis_combo.addItems(["X", "Y", "Z"])
        else:
            self.axis_combo.addItem("Z")  # rotation dans le plan XY

    def initializePage(self):
        """Afficher/masquer les options selon la dimension."""
        dim_page = self.wizard().page(MasonryWizard.PAGE_DIMENSION)
        is3d = dim_page.dim_3d_radio.isChecked()

        self.axis_combo.blockSignals(True)

        self.axis_combo.clear()
        if is3d:
            self.axis_combo.addItems(["X", "Y", "Z"])
            self.axis_combo.setCurrentText("Z")
        else:
            self.axis_combo.addItem("Z")
            self.axis_combo.setCurrentIndex(0)

        self.axis_combo.blockSignals(False)

        self.axis_combo.setEnabled(
            not is3d and self.rotate_check.isChecked()
        )



class MasonrySummaryPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("📋 Récapitulatif")
        self.setSubTitle("Vérifiez la configuration avant de générer.")

        layout = QVBoxLayout(self)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)

    def initializePage(self):
        wizard      = self.wizard()
        dim_page    = wizard.page(MasonryWizard.PAGE_DIMENSION)
        mat_page    = wizard.page(MasonryWizard.PAGE_MATERIAL)
        mod_page    = wizard.page(MasonryWizard.PAGE_MODEL)
        dim_brick   = wizard.page(MasonryWizard.PAGE_BRICK_DIM)
        layout_page = wizard.page(MasonryWizard.PAGE_LAYOUT)
        # tf_page utilisé plus bas dans la génération du résumé

        is3d      = dim_page.dim_3d_radio.isChecked()
        dimension = "3D" if is3d else "2D"

        mat_str = (
            f"Nouveau : <b>{mat_page.mat_name_input.text()}</b>"
            f" — {mat_page.density_spin.value()} kg/m³"
            if mat_page.create_material_check.isChecked()
            else f"Existant : <b>{mat_page.existing_combo.currentText()}</b>"
        )
        mod_str = (
            f"Nouveau : <b>{mod_page.mod_name_input.text()}</b>"
            if mod_page.create_model_check.isChecked()
            else f"Existant : <b>{mod_page.existing_combo.currentText()}</b>"
        )

        lx = dim_brick.lx_spin.value()
        ly = dim_brick.ly_spin.value()
        if is3d:
            lz = dim_brick.lz_spin.value()
            brick_api = (f"brick3D('{dim_brick.brick_name_input.text()}', "
                         f"lx={lx:.3f}, ly={ly:.3f}, lz={lz:.3f})")
            dim_str = f"lx={lx:.3f} m, ly={ly:.3f} m, lz={lz:.3f} m"
        else:
            lz = None
            brick_api = (f"brick2D('{dim_brick.brick_name_input.text()}', "
                         f"lx={lx:.3f}, ly={ly:.3f})")
            dim_str = f"lx={lx:.3f} m, ly={ly:.3f} m"

        nb_rows = layout_page.rows_spin.value()
        nb_cols = layout_page.cols_spin.value()
        joint   = layout_page.joint_spin.value()
        total   = nb_rows * nb_cols
        wall_w  = nb_cols * (lx + joint)
        wall_h  = nb_rows * ((lz if is3d else ly) + joint)
        pattern = layout_page.pattern_combo.currentText()

        summary = f"""
<h2>🧱 Mur en briques {dimension}</h2>
<table style="border-collapse:collapse; width:100%">
<tr><td style="padding:4px"><b>Dimension</b></td>
    <td>{dimension}</td></tr>
<tr><td style="padding:4px"><b>API pylmgc90</b></td>
    <td><code>{brick_api}</code></td></tr>
<tr><td style="padding:4px"><b>Matériau</b></td>
    <td>{mat_str}</td></tr>
<tr><td style="padding:4px"><b>Modèle</b></td>
    <td>{mod_str}</td></tr>
<tr><td style="padding:4px"><b>Dimensions brique</b></td>
    <td>{dim_str}</td></tr>
<tr><td style="padding:4px"><b>Appareil</b></td>
    <td>{pattern}</td></tr>
<tr><td style="padding:4px"><b>Rangs × colonnes</b></td>
    <td>{nb_rows} × {nb_cols} ≈ <b>{total} briques</b></td></tr>
<tr><td style="padding:4px"><b>Épaisseur joint</b></td>
    <td>{joint:.3f} m</td></tr>
<tr><td style="padding:4px"><b>Taille mur estimée</b></td>
    <td>{wall_w:.3f} m (L) × {wall_h:.3f} m (H)</td></tr>
<tr><td style="padding:4px"><b>Position</b></td>
    <td>({layout_page.offset_x_spin.value():.3f},
        {layout_page.offset_y_spin.value():.3f})</td></tr>
<tr><td style="padding:4px"><b>Couleur</b></td>
    <td>{layout_page.color_input.text() or 'BLUEx'}</td></tr>
"""
        if layout_page.store_check.isChecked():
            summary += (
                f"<tr><td style='padding:4px'><b>Groupe</b></td>"
                f"<td>{layout_page.group_name_input.text()}</td></tr>"
            )

        # ── Transformations ───────────────────────────────────────────────────
        tf_page = wizard.page(MasonryWizard.PAGE_TRANSFORM)
        if tf_page.translate_check.isChecked():
            summary += (
                f"<tr><td style='padding:4px'><b>Translation</b></td>"
                f"<td>dx={tf_page.tx_spin.value():.4f} m, "
                f"dy={tf_page.ty_spin.value():.4f} m"
                + (f", dz={tf_page.tz_spin.value():.4f} m" if is3d else "")
                + "</td></tr>"
            )
        if tf_page.rotate_check.isChecked():
            summary += (
                f"<tr><td style='padding:4px'><b>Rotation</b></td>"
                f"<td>axe {tf_page.axis_combo.currentText()}, "
                f"α={tf_page.alpha_spin.value():.2f}°, "
                f"centre=({tf_page.cx_spin.value():.4f}, "
                f"{tf_page.cy_spin.value():.4f}"
                + (f", {tf_page.cz_spin.value():.4f}" if is3d else "")
                + ")</td></tr>"
            )
        if tf_page.copy_check.isChecked():
            summary += (
                f"<tr><td style='padding:4px'><b>Copie décalée</b></td>"
                f"<td>dx={tf_page.copy_dx_spin.value():.4f} m, "
                f"dy={tf_page.copy_dy_spin.value():.4f} m"
                + (f", dz={tf_page.copy_dz_spin.value():.4f} m" if is3d else "")
                + "</td></tr>"
            )
        if pattern in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)"):
            pan_mode = ("Longueur fixe" if layout_page.pan_size_mode_combo.currentIndex() == 1
                        else "Nombre de briques")
            no_half  = layout_page.no_half_bricks_check.isChecked()
            summary += (
                f"<tr><td style='padding:4px'><b>Disposition</b></td>"
                f"<td>{layout_page.disposition_combo.currentText()}</td></tr>"
                f"<tr><td style='padding:4px'><b>1ère brique</b></td>"
                f"<td>{layout_page.first_brick_combo.currentText()}</td></tr>"
                f"<tr><td style='padding:4px'><b>Dimensionnement</b></td>"
                f"<td>{pan_mode}"
                + (f" — {layout_page.pan_length_spin.value():.3f} m"
                   if layout_page.pan_size_mode_combo.currentIndex() == 1 else "")
                + "</td></tr>"
                f"<tr><td style='padding:4px'><b>Sans demi-briques</b></td>"
                f"<td>{'Oui' if no_half else 'Non'}</td></tr>"
            )
        summary += "</table>"

        if total > 1000:
            summary += (
                f"<p style='color:orange'><b>⚠️ ~{total} briques — "
                "génération potentiellement lente.</b></p>"
            )
        summary += (
            "<hr>"
            "<p><b>✅ Cliquez sur « Générer » pour créer la structure.</b></p>"
        )
        self.summary_text.setHtml(summary)