"""
Générateur de scripts Python pour LMGC90.
Permet de créer des scripts reproductibles depuis l'état du projet.
"""

from pathlib import Path
from typing import TextIO

from ..controllers.project_controller import ProjectController
from ..core.models import (
    MaterialType, AvatarType, AvatarOrigin, ContactLawType
)


class ScriptGenerator:
    """Génère un script Python reproductible du projet"""
    
    def __init__(self, controller: ProjectController):
        self.controller = controller
        self.state = controller.state
    
    def generate(self, output_path: Path) -> None:
        """Génère le script complet"""
        with open(output_path, 'w', encoding='utf-8') as f:
            self._write_header(f)
            self._write_imports(f)
            self._write_containers(f)
            self._write_materials(f)
            self._write_models(f)
            self._write_avatars_manual(f)
            self._write_loops(f)
            self._write_granulo(f)
            self._write_contact_laws(f)
            self._write_visibility(f)
            self._write_dof_operations(f)
            self._write_postpro(f)
            self._write_datbox(f)
    
    def _write_header(self, f: TextIO):
        f.write(f'"""\n')
        f.write(f'Script généré automatiquement par LMGC90_GUI\n')
        f.write(f'Projet: {self.state.name}\n')
        f.write(f'Dimension: {self.state.dimension}D\n')
        f.write(f'"""\n\n')
    
    def _write_imports(self, f: TextIO):
        f.write('from pylmgc90 import pre\n')
        f.write('import numpy as np\n')
        f.write('import math\n\n')
    
    def _write_containers(self, f: TextIO):
        f.write('# Conteneurs\n')
        f.write('mats = pre.materials()\n')
        f.write('mods = pre.models()\n')
        f.write('bodies = pre.avatars()\n')
        f.write('tacts = pre.tact_behavs()\n')
        f.write('sees = pre.see_tables()\n')
        f.write('post = pre.postpro_commands()\n\n')
    
    def _write_materials(self, f: TextIO):
        if not self.state.materials:
            return
        
        f.write('# Matériaux\n')
        for mat in self.state.materials:
            f.write(f"mat_{mat.name} = pre.material(\n")
            f.write(f"    name='{mat.name}',\n")
            f.write(f"    materialType='{mat.material_type.value}',\n")
            f.write(f"    rho={mat.density}")
            
            if mat.properties:
                for key, value in mat.properties.items():
                    f.write(',\n    ')
                    if isinstance(value, str):
                        f.write(f"{key}='{value}'")
                    else:
                        f.write(f"{key}={value}")
            
            f.write('\n)\n')
            f.write(f"mats.addMaterial(mat_{mat.name})\n\n")
    
    def _write_models(self, f: TextIO):
        if not self.state.models:
            return
        
        f.write('# Modèles\n')
        for mod in self.state.models:
            f.write(f"mod_{mod.name} = pre.model(\n")
            f.write(f"    name='{mod.name}',\n")
            f.write(f"    physics='{mod.physics}',\n")
            f.write(f"    element='{mod.element}'")
            
            if mod.options:
                for key, value in mod.options.items():
                    f.write(',\n    ')
                    if isinstance(value, str):
                        f.write(f"{key}='{value}'")
                    else:
                        f.write(f"{key}={value}")
            
            f.write('\n)\n')
            f.write(f"mods.addModel(mod_{mod.name})\n\n")
    
    def _write_avatars_manual(self, f: TextIO):
        manual_avatars = [a for a in self.state.avatars if a.origin == AvatarOrigin.MANUAL]
        if not manual_avatars:
            return
        
        f.write('# Avatars manuels\n')
        for i, av in enumerate(manual_avatars):
            self._write_single_avatar(f, av, f"av_manual_{i}")
        f.write('\n')
    
    def _write_single_avatar(self, f: TextIO, av, var_name: str):
        avatar_type = av.avatar_type.value
        
        f.write(f"{var_name} = pre.{avatar_type}(\n")
        f.write(f"    center={av.center},\n")
        f.write(f"    material=mat_{av.material_name},\n")
        f.write(f"    model=mod_{av.model_name},\n")
        f.write(f"    color='{av.color}'")
        
        if av.radius is not None:
            f.write(f",\n    r={av.radius}")
        
        if av.is_hollow:
            f.write(f",\n    is_Hollow=True")
        
        if av.axis:
            for key, val in av.axis.items():
                f.write(f",\n    {key}={val}")
        
        if av.nb_vertices is not None:
            f.write(f",\n    nb_vertices={av.nb_vertices}")
        
        if av.generation_type:
            f.write(f",\n    gen_type='{av.generation_type}'")
        
        if av.vertices:
            f.write(f",\n    vertices={av.vertices}")
        
        if av.wall_params:
            for key, val in av.wall_params.items():
                f.write(f",\n    {key}={val}")
        
        if av.contactors:
            f.write(f",\n    contactors=[\n")
            for cont in av.contactors:
                f.write(f"        {cont},\n")
            f.write(f"    ]")
        
        f.write('\n)\n')
        f.write(f"bodies.addAvatar({var_name})\n\n")
    
    def _write_loops(self, f: TextIO):
        if not self.state.loops:
            return
        
        f.write('# Boucles\n')
        for i, loop in enumerate(self.state.loops):
            f.write(f"# Boucle {i+1}: {loop.loop_type}\n")
            
            model_avatar = self.state.avatars[loop.model_avatar_index]
            
            if loop.loop_type == "Cercle":
                f.write(f"for angle_idx in range({loop.count}):\n")
                f.write(f"    angle = 2 * math.pi * angle_idx / {loop.count}\n")
                f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x} + {loop.radius} * math.cos(angle)\n")
                f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y} + {loop.radius} * math.sin(angle)\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            
            elif loop.loop_type == "Grille":
                n_side = int(loop.count ** 0.5)
                f.write(f"n_side = {n_side}\n")
                f.write(f"for i in range(n_side):\n")
                f.write(f"    for j in range(n_side):\n")
                f.write(f"        x = {model_avatar.center[0]} + {loop.offset_x} + i * {loop.step}\n")
                f.write(f"        y = {model_avatar.center[1]} + {loop.offset_y} + j * {loop.step}\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            
            elif loop.loop_type == "Ligne":
                axis = 1 if loop.invert_axis else 0
                f.write(f"for idx in range({loop.count}):\n")
                if axis == 0:
                    f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x} + idx * {loop.step}\n")
                    f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y}\n")
                else:
                    f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x}\n")
                    f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y} + idx * {loop.step}\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            
            elif loop.loop_type == "Spirale":
                f.write(f"for idx in range({loop.count}):\n")
                f.write(f"    angle = 2 * math.pi * idx / 10\n")
                f.write(f"    r = {loop.radius} + idx * {loop.spiral_factor}\n")
                f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x} + r * math.cos(angle)\n")
                f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y} + r * math.sin(angle)\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            else:
                continue
            
            indent = "    " if loop.loop_type == "Grille" else "    "
            if loop.loop_type == "Grille":
                indent = "        "
            
            f.write(f"{indent}center = {center_calc}\n")
            f.write(f"{indent}av = pre.{model_avatar.avatar_type.value}(\n")
            f.write(f"{indent}    center=center,\n")
            f.write(f"{indent}    material=mat_{model_avatar.material_name},\n")
            f.write(f"{indent}    model=mod_{model_avatar.model_name},\n")
            f.write(f"{indent}    color='{model_avatar.color}'")
            
            if model_avatar.radius is not None:
                f.write(f",\n{indent}    r={model_avatar.radius}")
            
            f.write(f"\n{indent})\n")
            f.write(f"{indent}bodies.addAvatar(av)\n\n")
    
    def _write_granulo(self, f: TextIO):
        if not self.state.granulo_generations:
            return
        
        f.write('# Génération granulométrique\n')
        for i, gen in enumerate(self.state.granulo_generations):
            f.write(f"# Dépôt granulo {i+1}\n")
            
            container_params_str = ', '.join(f"{k}={v}" for k, v in gen.container_params.items())
            
            f.write(f"nb_particles_{i}, coords_{i}, radii_{i} = pre.{gen.container_type}(\n")
            f.write(f"    nb={gen.nb_particles},\n")
            f.write(f"    rmin={gen.radius_min},\n")
            f.write(f"    rmax={gen.radius_max}")
            if gen.seed:
                f.write(f",\n    seed={gen.seed}")
            if container_params_str:
                f.write(f",\n    {container_params_str}")
            f.write(f"\n)\n\n")
            
            f.write(f"for j in range(nb_particles_{i}):\n")
            f.write(f"    av = pre.{gen.avatar_type}(\n")
            f.write(f"        center=coords_{i}[j].tolist(),\n")
            f.write(f"        material=mat_{gen.material_name},\n")
            f.write(f"        model=mod_{gen.model_name},\n")
            f.write(f"        color='{gen.color}',\n")
            f.write(f"        r=float(radii_{i}[j])\n")
            f.write(f"    )\n")
            f.write(f"    bodies.addAvatar(av)\n\n")
    
    def _write_contact_laws(self, f: TextIO):
        if not self.state.contact_laws:
            return
        
        f.write('# Lois de contact\n')
        for law in self.state.contact_laws:
            f.write(f"law_{law.name} = pre.tact_behav(\n")
            f.write(f"    name='{law.name}',\n")
            f.write(f"    law='{law.law_type.value}'")
            
            if law.friction is not None:
                f.write(f",\n    fric={law.friction}")
            
            if law.properties:
                for key, value in law.properties.items():
                    f.write(',\n    ')
                    if isinstance(value, str):
                        f.write(f"{key}='{value}'")
                    else:
                        f.write(f"{key}={value}")
            
            f.write('\n)\n')
            f.write(f"tacts.addBehav(law_{law.name})\n\n")
    
    def _write_visibility(self, f: TextIO):
        if not self.state.visibility_rules:
            return
        
        f.write('# Tables de visibilité\n')
        for i, rule in enumerate(self.state.visibility_rules):
            f.write(f"see_{i} = pre.see_table(\n")
            f.write(f"    CorpsCandidat='{rule.candidate_body}',\n")
            f.write(f"    candidat='{rule.candidate_contactor}',\n")
            f.write(f"    colorCandidat='{rule.candidate_color}',\n")
            f.write(f"    CorpsAntagoniste='{rule.antagonist_body}',\n")
            f.write(f"    antagoniste='{rule.antagonist_contactor}',\n")
            f.write(f"    colorAntagoniste='{rule.antagonist_color}',\n")
            f.write(f"    behav=law_{rule.behavior_name},\n")
            f.write(f"    alert={rule.alert}\n")
            f.write(f")\n")
            f.write(f"sees.addSeeTable(see_{i})\n\n")
    
    def _write_dof_operations(self, f: TextIO):
        if not self.state.operations:
            return
        
        f.write('# Opérations DOF\n')
        for i, op in enumerate(self.state.operations):
            params_str = ', '.join(f"{k}={repr(v)}" for k, v in op.parameters.items())
            
            if op.target_type == 'avatar':
                f.write(f"# DOF sur avatar #{op.target_value}\n")
                f.write(f"# bodies.get({op.target_value}).{op.operation_type}({params_str})\n\n")
            elif op.target_type == 'group':
                f.write(f"# DOF sur groupe '{op.target_value}'\n")
                f.write(f"# for av in group_{op.target_value}:\n")
                f.write(f"#     av.{op.operation_type}({params_str})\n\n")
    
    def _write_postpro(self, f: TextIO):
        if not self.state.postpro_commands:
            return
        
        f.write('# Post-traitement\n')
        for i, cmd in enumerate(self.state.postpro_commands):
            if cmd.target_type and cmd.target_value is not None:
                f.write(f"# Commande avec cible: {cmd.target_type} = {cmd.target_value}\n")
                f.write(f"# rigid_set = [...]  # À définir selon la cible\n")
                f.write(f"# post_cmd_{i} = pre.postpro_command(\n")
                f.write(f"#     name='{cmd.name}',\n")
                f.write(f"#     step={cmd.step},\n")
                f.write(f"#     rigid_set=rigid_set\n")
                f.write(f"# )\n")
            else:
                f.write(f"post = pre.postpro_commands()")
                f.write(f"post_cmd_{i} = pre.postpro_command(\n")
                f.write(f"    name='{cmd.name}',\n")
                f.write(f"    step={cmd.step}\n")
                f.write(f")\n")
                f.write(f"post.addCommand(post_cmd_{i})\n")
            f.write('\n')
    
    def _write_datbox(self, f: TextIO):
        f.write('# Génération DATBOX\n')
        f.write(f"pre.writeDatbox(\n")
        f.write(f"    dim={self.state.dimension},\n")
        f.write(f"    mats=mats,\n")
        f.write(f"    mods=mods,\n")
        f.write(f"    bodies=bodies,\n")
        f.write(f"    tacts=tacts,\n")
        f.write(f"    sees=sees,\n")
        f.write(f"    post=post,\n")
        f.write(f"    datbox_path='DATBOX'\n")
        f.write(f")\n\n")
        f.write(f"print('DATBOX généré avec succès!')\n")
    """Génère un script Python exécutable depuis l'état du projet"""
    
    def __init__(self, controller: 'ProjectController'):
        self.controller = controller
        self.state = controller.state
    
    def generate(self, output_path: Path) -> None:
        """
        Génère le script Python complet.
        
        Args:
            output_path: Chemin du fichier de sortie (.py)
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            self._write_header(f)
            self._write_imports(f)
            self._write_containers(f)
            self._write_materials(f)
            self._write_models(f)
            self._write_avatars(f)
            self._write_loops(f)
            self._write_granulo(f)
            self._write_dof_operations(f)
            self._write_contact_laws(f)
            self._write_visibility(f)
            self._write_postpro(f)
            self._write_footer(f)
    
    def _write_header(self, f):
        """En-tête du script"""
        f.write("# -*- coding: utf-8 -*-\n")
        f.write(f'"""\n')
        f.write(f'Script LMGC90 généré automatiquement\n')
        f.write(f'Projet : {self.state.name}\n')
        f.write(f'Généré par LMGC90_GUI v0.3.0\n')
        f.write(f'"""\n\n')
    
    def _write_imports(self, f):
        """Imports nécessaires"""
        f.write("from pylmgc90 import pre\n")
        f.write("import numpy as np\n")
        f.write("import math\n\n")
    
    def _write_containers(self, f):
        """Conteneurs LMGC90"""
        f.write("# ============================================\n")
        f.write("# CONTENEURS\n")
        f.write("# ============================================\n\n")
        f.write("materials = pre.materials()\n")
        f.write("models = pre.models()\n")
        f.write("bodies = pre.avatars()\n")
        f.write("tacts = pre.tact_behavs()\n")
        f.write("see_tables = pre.see_tables()\n")
        f.write("post = pre.postpro_commands()\n\n")
        f.write("# Dictionnaires pour référencer facilement\n")
        f.write("mats = {}\n")
        f.write("mods = {}\n")
        f.write("laws = {}\n")
        f.write("bodies_list = []\n\n")
    
    def _write_materials(self, f):
        """Matériaux"""
        if not self.state.materials:
            return
        
        f.write("# ============================================\n")
        f.write("# MATÉRIAUX\n")
        f.write("# ============================================\n\n")
        
        for mat in self.state.materials:
            props_str = ""
            if mat.properties:
                props = ", ".join(f"{k}={self._format_value(v)}" 
                                 for k, v in mat.properties.items())
                props_str = f", {props}"
            
            f.write(f"mats['{mat.name}'] = pre.material(\n")
            f.write(f"    name='{mat.name}',\n")
            f.write(f"    materialType='{mat.material_type.value}',\n")
            f.write(f"    density={mat.density}{props_str}\n")
            f.write(f")\n")
            f.write(f"materials.addMaterial(mats['{mat.name}'])\n\n")
    
    def _write_models(self, f):
        """Modèles"""
        if not self.state.models:
            return
        
        f.write("# ============================================\n")
        f.write("# MODÈLES\n")
        f.write("# ============================================\n\n")
        
        for mod in self.state.models:
            opts_str = ""
            if mod.options:
                opts = ", ".join(f"{k}='{v}'" for k, v in mod.options.items())
                opts_str = f", {opts}"
            
            f.write(f"mods['{mod.name}'] = pre.model(\n")
            f.write(f"    name='{mod.name}',\n")
            f.write(f"    physics='{mod.physics}',\n")
            f.write(f"    element='{mod.element}',\n")
            f.write(f"    dimension={mod.dimension}{opts_str}\n")
            f.write(f")\n")
            f.write(f"models.addModel(mods['{mod.name}'])\n\n")
    
    def _write_avatars(self, f):
        """Avatars manuels seulement"""
        from ..core.models import AvatarOrigin
        manual_avatars = [a for a in self.state.avatars if a.origin == AvatarOrigin.MANUAL]
        
        if not manual_avatars:
            return
        
        f.write("# ============================================\n")
        f.write("# AVATARS MANUELS\n")
        f.write("# ============================================\n\n")
        
        for avatar in manual_avatars:
            self._write_single_avatar(f, avatar, "bodies")
    
    def _write_single_avatar(self, f, avatar, container="bodies"):
        """Écrit un avatar individuel"""
        atype = avatar.avatar_type.value
        center = avatar.center
        mat = avatar.material_name
        mod = avatar.model_name
        color = avatar.color
        
        # emptyAvatar
        if atype == "emptyAvatar":
            f.write(f"# Avatar vide avec contacteurs personnalisés\n")
            f.write(f"body = pre.avatar(dimension={len(center)})\n")
            
            # Bulk
            if len(center) == 2:
                f.write(f"body.addBulk(pre.rigid2d())\n")
            else:
                f.write(f"body.addBulk(pre.rigid3d())\n")
            
            # Node principal
            f.write(f"body.addNode(pre.node(coor=np.array({center}), number=1))\n")
            
            # Configuration
            f.write(f"body.defineGroups()\n")
            f.write(f"body.defineModel(model=mods['{mod}'])\n")
            f.write(f"body.defineMaterial(material=mats['{mat}'])\n")
            
            # Contacteurs
            for cont in avatar.contactors:
                shape = cont['shape']
                color_c = cont.get('color', color)
                params = cont.get('params', {})
                
                # Construire les paramètres
                params_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
                
                f.write(f"body.addContactors(shape='{shape}', color='{color_c}'")
                if params_str:
                    f.write(f", {params_str}")
                f.write(f")\n")
            
            # Calcul des propriétés rigides
            f.write(f"body.computeRigidProperties()\n")
            f.write(f"{container}.addAvatar(body)\n")
            f.write("bodies_list.append(body)\n\n")
            return
        
        # avatars standards
        # construire les arguments
        args = [
            f"center={center}",
            f"model=mods['{mod}']",
            f"material=mats['{mat}']",
            f"color='{color}'"
        ]
        
        # Arguments spécifiques selon le type
        if avatar.radius is not None:
            args.append(f"r={avatar.radius}")
        
        if avatar.axis:
            args.append(f"axe1={avatar.axis['axe1']}")
            args.append(f"axe2={avatar.axis['axe2']}")
        
        if avatar.generation_type:
            args.append(f"generation_type='{avatar.generation_type}'")
        
        if avatar.nb_vertices:
            args.append(f"nb_vertices={avatar.nb_vertices}")
        
        if avatar.vertices:
            args.append(f"vertices=np.array({avatar.vertices})")
        
        if avatar.is_hollow:
            args.append("is_Hollow=True")
        
        if avatar.wall_params:
            for k, v in avatar.wall_params.items():
                args.append(f"{k}={v}")
        
        # Écrire
        f.write(f"body = pre.{atype}(\n")
        for i, arg in enumerate(args):
            f.write(f"    {arg}")
            if i < len(args) - 1:
                f.write(",\n")
            else:
                f.write("\n")
        f.write(")\n")
        f.write(f"{container}.addAvatar(body)\n")
        f.write("bodies_list.append(body)\n\n")
    
    def _write_loops(self, f):
        """Boucles"""
        if not self.state.loops:
            return
        
        f.write("# ============================================\n")
        f.write("# BOUCLES\n")
        f.write("# ============================================\n\n")
        
        for idx, loop in enumerate(self.state.loops):
            f.write(f"# Boucle {idx + 1} : {loop.loop_type}\n")
            
            if loop.model_avatar_index >= len(self.state.avatars):
                f.write(f"# ERREUR : Index modèle invalide\n\n")
                continue
            
            model_avatar = self.state.avatars[loop.model_avatar_index]
            
            # Générer les centres
            f.write("centers = []\n")
            
            if loop.loop_type == "Cercle":
                f.write(f"for i in range({loop.count}):\n")
                f.write(f"    angle = 2 * math.pi * i / {loop.count}\n")
                f.write(f"    x = {loop.offset_x} + {loop.radius} * math.cos(angle)\n")
                f.write(f"    y = {loop.offset_y} + {loop.radius} * math.sin(angle)\n")
                f.write(f"    centers.append([x, y])\n\n")
            
            elif loop.loop_type == "Grille":
                side = int((loop.count ** 0.5)) + 1
                f.write(f"for i in range({loop.count}):\n")
                f.write(f"    x = {loop.offset_x} + (i % {side}) * {loop.step}\n")
                f.write(f"    y = {loop.offset_y} + (i // {side}) * {loop.step}\n")
                f.write(f"    centers.append([x, y])\n\n")
            
            elif loop.loop_type == "Ligne":
                f.write(f"for i in range({loop.count}):\n")
                if loop.invert_axis:
                    f.write(f"    centers.append([{loop.offset_x}, {loop.offset_y} + i * {loop.step}])\n\n")
                else:
                    f.write(f"    centers.append([{loop.offset_x} + i * {loop.step}, {loop.offset_y}])\n\n")
            
            elif loop.loop_type == "Spirale":
                f.write(f"for i in range({loop.count}):\n")
                f.write(f"    angle = 2 * math.pi * i / max(1, {loop.count} // 5)\n")
                f.write(f"    r = {loop.radius} + i * {loop.spiral_factor}\n")
                f.write(f"    x = {loop.offset_x} + r * math.cos(angle)\n")
                f.write(f"    y = {loop.offset_y} + r * math.sin(angle)\n")
                f.write(f"    centers.append([x, y])\n\n")
            
            # Créer les avatars
            f.write("for center in centers:\n")
            self._write_loop_avatar(f, model_avatar)
    
    def _write_loop_avatar(self, f, avatar):
        """Écrit la création d'un avatar dans une boucle"""
        atype = avatar.avatar_type.value
        
        if atype == "emptyAvatar":
            f.write(f"    # Avatar vide\n")
            f.write(f"    body = pre.avatar(dimension={len(avatar.center)})\n")
            
            if len(avatar.center) == 2:
                f.write(f"    body.addBulk(pre.rigid2d())\n")
            else:
                f.write(f"    body.addBulk(pre.rigid3d())\n")
            
            f.write(f"    body.addNode(pre.node(coor=np.array(center), number=1))\n")
            f.write(f"    body.defineGroups()\n")
            f.write(f"    body.defineModel(model=mods['{avatar.model_name}'])\n")
            f.write(f"    body.defineMaterial(material=mats['{avatar.material_name}'])\n")
            
            for cont in avatar.contactors:
                shape = cont['shape']
                color_c = cont.get('color', avatar.color)
                params = cont.get('params', {})
                params_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
                
                f.write(f"    body.addContactors(shape='{shape}', color='{color_c}'")
                if params_str:
                    f.write(f", {params_str}")
                f.write(f")\n")
            
            f.write(f"    body.computeRigidProperties()\n")
            f.write("    bodies.addAvatar(body)\n")
            f.write("    bodies_list.append(body)\n\n")
            return
        
        # avatars standards
        f.write(f"    body = pre.{atype}(center=center, ")
        f.write(f"model=mods['{avatar.model_name}'], ")
        f.write(f"material=mats['{avatar.material_name}'], ")
        f.write(f"color='{avatar.color}'")
        
        if avatar.radius:
            f.write(f", r={avatar.radius}")
        
        f.write(")\n")
        f.write("    bodies.addAvatar(body)\n")
        f.write("    bodies_list.append(body)\n\n")
    
    def _write_granulo(self, f):
        """Granulométrie"""
        if not self.state.granulo_generations:
            return
        
        f.write("# ============================================\n")
        f.write("# GRANULOMÉTRIE\n")
        f.write("# ============================================\n\n")
        
        for idx, gen in enumerate(self.state.granulo_generations):
            f.write(f"# Génération granulo {idx + 1}\n")
            
            seed_str = f", {gen.seed}" if gen.seed else ""
            f.write(f"radii = pre.granulo_Random({gen.nb_particles}, {gen.radius_min}, {gen.radius_max}{seed_str})\n")
            
            # Dépôt
            ctype = gen.container_type
            params = gen.container_params
            
            if ctype == "Box2D":
                f.write(f"nb_remaining, coor = pre.depositInBox2D(radii, {params['lx']}, {params['ly']})\n")
            elif ctype == "Disk2D":
                f.write(f"nb_remaining, coor = pre.depositInDisk2D(radii, {params['r']})\n")
            elif ctype == "Couette2D":
                f.write(f"nb_remaining, coor = pre.depositInCouette2D(radii, {params['rint']}, {params['rext']})\n")
            elif ctype == "Drum2D":
                f.write(f"nb_remaining, coor = pre.depositInDrum2D(radii, {params['r']})\n")
            
            f.write("nb_remaining = np.shape(coor)[0] // 2\n")
            f.write("coor = np.reshape(coor, (nb_remaining, 2))\n\n")
            
            f.write("for i in range(nb_remaining):\n")
            f.write(f"    body = pre.{gen.avatar_type}(\n")
            f.write(f"        r=radii[i],\n")
            f.write(f"        center=coor[i],\n")
            f.write(f"        model=mods['{gen.model_name}'],\n")
            f.write(f"        material=mats['{gen.material_name}'],\n")
            f.write(f"        color='{gen.color}'\n")
            f.write(f"    )\n")
            f.write(f"    bodies.addAvatar(body)\n")
            f.write(f"    bodies_list.append(body)\n\n")
    
    def _write_dof_operations(self, f):
        """Opérations DOF"""
        if not self.state.operations:
            return
        
        f.write('# ============================================\n')
        f.write('# CONDITIONS AUX LIMITES (DOF)\n')
        f.write('# ============================================\n\n')
        
        for op in self.state.operations:
            params = ", ".join(f"{k}={repr(v)}" for k, v in op.parameters.items())
            
            if op.target_type == 'avatar':
                # Opération sur un avatar individuel
                f.write(f"# DOF sur avatar #{op.target_value}\n")
                f.write(f"bodies_list[{op.target_value}].{op.operation_type}({params})\n\n")
            
            elif op.target_type == 'group':
                # Opération sur un groupe - CORRECTION ICI
                group_name = op.target_value
                indices = self.state.avatar_groups.get(group_name, [])
                
                if not indices:
                    f.write(f"# Groupe '{group_name}' vide ou introuvable\n\n")
                    continue
                
                f.write(f"# DOF sur groupe '{group_name}' ({len(indices)} avatars)\n")
                f.write(f"for avatar_idx in {indices}:\n")
                f.write(f"    bodies_list[avatar_idx].{op.operation_type}({params})\n")
        
        f.write("\n")
    
    def _write_contact_laws(self, f):
        """Lois de contact"""
        if not self.state.contact_laws:
            return
        
        f.write("# ============================================\n")
        f.write("# LOIS DE CONTACT\n")
        f.write("# ============================================\n\n")
        
        for law in self.state.contact_laws:
            fric_str = f", fric={law.friction}" if law.friction else ""
            f.write(f"laws['{law.name}'] = pre.tact_behav(\n")
            f.write(f"    name='{law.name}',\n")
            f.write(f"    law='{law.law_type.value}'{fric_str}\n")
            f.write(f")\n")
            f.write(f"tacts.addBehav(laws['{law.name}'])\n\n")
    
    def _write_visibility(self, f):
        """Tables de visibilité"""
        if not self.state.visibility_rules:
            return
        
        f.write("# ============================================\n")
        f.write("# TABLES DE VISIBILITÉ\n")
        f.write("# ============================================\n\n")
        
        for rule in self.state.visibility_rules:
            f.write(f"see_table = pre.see_table(\n")
            f.write(f"    CorpsCandidat='{rule.candidate_body}',\n")
            f.write(f"    candidat='{rule.candidate_contactor}',\n")
            f.write(f"    colorCandidat='{rule.candidate_color}',\n")
            f.write(f"    CorpsAntagoniste='{rule.antagonist_body}',\n")
            f.write(f"    antagoniste='{rule.antagonist_contactor}',\n")
            f.write(f"    colorAntagoniste='{rule.antagonist_color}',\n")
            f.write(f"    behav=laws['{rule.behavior_name}'],\n")
            f.write(f"    alert={rule.alert}\n")
            f.write(f")\n")
            f.write(f"see_tables.addSeeTable(see_table)\n\n")
    
    def _write_postpro(self, f):
        """Commandes post-pro"""
        if not self.state.postpro_commands:
            return
        
        f.write("# ============================================\n")
        f.write("# POST-TRAITEMENT\n")
        f.write("# ============================================\n\n")
        
        for cmd in self.state.postpro_commands:
            if cmd.target_type and cmd.target_value is not None:
                f.write(f"# {cmd.name} avec cible\n")
                f.write(f"# TODO: Implémenter rigid_set\n")
            else:
                f.write(f"post.addCommand(pre.postpro_command(name='{cmd.name}', step={cmd.step}))\n")
        
        f.write("\n")
    
    def _write_footer(self, f):
        """Pied de page - Écriture DATBOX"""
        f.write("# ============================================\n")
        f.write("# ÉCRITURE DATBOX\n")
        f.write("# ============================================\n\n")
        f.write(f"pre.writeDatbox(\n")
        f.write(f"    dim={self.state.dimension},\n")
        f.write(f"    mats=materials,\n")
        f.write(f"    mods=models,\n")
        f.write(f"    bodies=bodies,\n")
        f.write(f"    tacts=tacts,\n")
        f.write(f"    sees=see_tables,\n")
        f.write(f"    post=post\n")
        f.write(f")\n\n")
        f.write(f'print("DATBOX généré avec succès !")\n')
    
    def _format_value(self, value):
        """Formate une valeur pour Python"""
        if isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return "True" if value else "False"
        else:
            return repr(value)