# ============================================================================
# Pont vers pylmgc90
# ============================================================================
"""
Pont entre nos modèles et les objets pylmgc90.
Gère la conversion et la création d'objets LMGC90.
"""
import numpy as np
from typing import Dict, List, Any, TYPE_CHECKING

try:
    from pylmgc90 import pre
except ModuleNotFoundError:  # pragma: no cover - fallback pour tests/CI
    class _FallbackPre:
        def __getattr__(self, name):
            def _missing(*args, **kwargs):
                return None
            return _missing

    pre = _FallbackPre()

from .models import (
    Material, Model, Avatar, ContactLaw, VisibilityRule,
    DOFOperation, AvatarType, MaterialType, ContactLawType
)

if TYPE_CHECKING:
    from .particle_population import ParticlePopulation


class LMGC90Bridge:
    """Convertit entre nos modèles et pylmgc90"""
    
    @staticmethod
    def create_material(material: Material) -> Any:
        """Crée un objet material pylmgc90"""
        mat_type = material.material_type.value
        
        if mat_type in ["RIGID", "ELAS", "ELAS_DILA", "VISCO_ELAS", 
                        "ELAS_PLAS", "THERMO_ELAS", "PORO_ELAS", 
                        "DISCRETE", "USER_MAT", "EXTERNAL"]:
            return pre.material(
                name=material.name,
                materialType=mat_type,
                density=material.density,
                **material.properties
            )
        else:
            raise ValueError(f"Type de matériau non supporté: {mat_type}")
    
    @staticmethod
    def create_model(model: Model) -> Any:
        """Crée un objet model pylmgc90"""
        if model.element in ["Rxx2D", "Rxx3D"]:
            return pre.model(
                name=model.name,
                physics=model.physics,
                element=model.element,
                dimension=model.dimension
            )
        else:
            return pre.model(
                name=model.name,
                physics=model.physics,
                element=model.element,
                dimension=model.dimension,
                **model.options
            )
    
    @staticmethod
    def create_avatar(avatar: Avatar, model_obj: Any, material_obj: Any) -> Any:
        """
        Crée un objet avatar pylmgc90.
        
        Args:
            avatar: Modèle d'avatar
            model_obj: Objet model pylmgc90
            material_obj: Objet material pylmgc90
            
        Returns:
            Objet avatar pylmgc90
        """
        atype = avatar.avatar_type
        center = np.ascontiguousarray(avatar.center, dtype=np.float64)
        color = avatar.color
        
        # Création selon le type
        # 2D avatars
        if atype == AvatarType.RIGID_DISK:
            radius = float(avatar.radius)
            if center.shape != (2,) or not np.isfinite(center).all() or not np.isfinite(radius) or radius <= 0:
                raise ValueError(
                    f"Paramètres rigidDisk invalides: center={center!r}, radius={radius!r}"
                )
            kwargs = {
                'r': radius,
                'center': center,
                'model': model_obj,
                'material': material_obj,
                'color': color
            }
            if avatar.is_hollow:
                kwargs['is_Hollow'] = True
            from .app_logger import get_logger
            logger = get_logger('pylmgc_bridge')
            logger.debug("rigidDisk avant: center=%s radius=%s", center.tolist(), radius)
            body = pre.rigidDisk(**kwargs)
            logger.debug("rigidDisk après")
            return body
        
        elif atype == AvatarType.RIGID_JONC:
            return pre.rigidJonc(
                axe1=avatar.axis['axe1'],
                axe2=avatar.axis['axe2'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_POLYGON:
            if avatar.generation_type == "regular":
                return pre.rigidPolygon(
                    model=model_obj,
                    material=material_obj,
                    center=center,
                    color=color,
                    generation_type=avatar.generation_type,
                    nb_vertices=avatar.nb_vertices,
                    radius=avatar.radius
                )
            else:
                return pre.rigidPolygon(
                    model=model_obj,
                    material=material_obj,
                    center=center,
                    color=color,
                    generation_type=avatar.generation_type,
                    vertices=np.array(avatar.vertices, dtype=float),
                    radius=avatar.radius
                )
        
        elif atype == AvatarType.RIGID_OVOID:
            return pre.rigidOvoidPolygon(
                ra=avatar.wall_params['ra'],
                rb=avatar.wall_params['rb'],
                nb_vertices=avatar.nb_vertices,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_DISCRETE:
            return pre.rigidDiscreteDisk(
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_CLUSTER:
            return pre.rigidCluster(
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_disk=avatar.nb_vertices
            )
        
        elif atype == AvatarType.ROUGH_WALL:
            return pre.roughWall(
                l=avatar.wall_params['l'],
                r=avatar.wall_params['r'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_vertex=avatar.wall_params.get('nb_vertex', 10)
            )
        
        elif atype == AvatarType.FINE_WALL:
            return pre.fineWall(
                l=avatar.wall_params['l'],
                r=avatar.wall_params['r'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_vertex=avatar.wall_params.get('nb_vertex', 10)
            )
        
        elif atype == AvatarType.SMOOTH_WALL:
            return pre.smoothWall(
                l=avatar.wall_params['l'],
                h=avatar.wall_params['h'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_polyg=avatar.wall_params.get('nb_polyg', 10)
            )
        
        elif atype == AvatarType.GRANULO_WALL:
            return pre.granuloRoughWall(
                l=avatar.wall_params['l'],
                rmin=avatar.wall_params['rmin'],
                rmax=avatar.wall_params['rmax'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_vertex=avatar.wall_params.get('nb_vertex', 10)
            )
        
        elif atype == AvatarType.EMPTY_AVATAR:
            # Reconstruction via pre.brick2D / pre.brick3D + rigidBrick()
            wp = avatar.wall_params or {}
            if 'l' in wp and 'h' in wp:
                brick_name = wp.get('brick_name', 'std')
                bx  = wp['l']       # longueur
                by  = wp['h']       # hauteur (2D) ou profondeur (3D)
                bz  = wp.get('lz')  # hauteur 3D, None en 2D
                dim = len(center)
                if dim == 2:
                    # brick2D(name, lx, ly) : lx=longueur, ly=hauteur
                    brick = pre.brick2D(brick_name, bx, by)
                else:
                    # brick3D(name, lx, ly, lz) : lx=longueur, ly=profondeur, lz=hauteur
                    if bz is None:
                        bz = by  # fallback de securite
                    brick = pre.brick3D(brick_name, bx, by, bz)
                return brick.rigidBrick(
                    center=np.array(center),
                    model=model_obj,
                    material=material_obj,
                    color=color
                )
            # Avatar vide avec contacteurs personnalisés
            body = pre.avatar(dimension=len(center))
            
            # Bulk
            if len(center) == 2:
                body.addBulk(pre.rigid2d())
            else:
                body.addBulk(pre.rigid3d())
            
            # Node principal
            body.addNode(pre.node(coor=np.array(center), number=1))
            
            # Configuration
            body.defineGroups()
            body.defineModel(model=model_obj)
            body.defineMaterial(material=material_obj)
            
            # Contacteurs
            for cont in avatar.contactors:
                shape = cont['shape']
                color_c = cont.get('color', color)
                params = cont.get('params', {})
                
                body.addContactors(
                    shape=shape,
                    color=color_c,
                    **params
                )
            
            # Calcul des propriétés rigides
            body.computeRigidProperties()
            
            return body
        
        # Avatars 3D
        elif atype == AvatarType.RIGID_SPHERE:
            kwargs = dict(
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
            if avatar.is_hollow:
                kwargs['is_Hollow'] = True
            return pre.rigidSphere(**kwargs)
    
        elif atype == AvatarType.RIGID_PLAN:
            return pre.rigidPlan(
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                axe1=avatar.axis['axe1'],
                axe2=avatar.axis['axe2'],
                axe3=avatar.axis['axe3']
            )
        
        elif atype == AvatarType.RIGID_CYLINDER:
            kwargs = dict(
                r=avatar.radius,
                h=avatar.wall_params.get('h', 1.0) if avatar.wall_params else 1.0,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
            if avatar.is_hollow:
                kwargs['is_Hollow'] = True
            return pre.rigidCylinder(**kwargs)
        
        elif atype == AvatarType.RIGID_POLYHEDRON:
            if avatar.generation_type == "regular":
                return pre.rigidPolyhedron(
                    nb_vertices=avatar.nb_vertices,
                    vertices=None,
                    radius=avatar.radius,
                    generation_type=avatar.generation_type,
                    center=center,
                    model=model_obj,
                    material=material_obj,
                    color=color,
                    faces=None)
                
            else : 
                return pre.rigidPolyhedron(
                    nb_vertices=avatar.nb_vertices,
                    vertices=np.array(avatar.vertices) if avatar.vertices else np.array([]),
                    generation_type=avatar.generation_type,
                    center=center,
                    model=model_obj,
                    material=material_obj,
                    color=color,
                    radius=avatar.radius,
                    faces=avatar.wall_params.get('faces', [])
            )
        
        elif atype == AvatarType.ROUGH_WALL_3D:
            return pre.roughWall3D(
                lx=avatar.wall_params['lx'],
                ly=avatar.wall_params['ly'],
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.GRANULO_ROUGH_WALL_3D:
            return pre.granuloRoughWall3D(
                lx=avatar.wall_params['lx'],
                ly=avatar.wall_params['ly'],
                rmin=avatar.wall_params['rmin'],
                rmax=avatar.wall_params['rmax'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        elif atype == AvatarType.MESH_DEFORMABLE:
            mp = avatar.mesh_params 
            if not mp:
               return None

            geom = mp['geom']
            dim  = mp['dim']
            cx   = mp.get('cx', 0.0)
            cy   = mp.get('cy', 0.0)
            cz   = mp.get('cz', 0.0)

            if geom == "Rectangle":
                from pylmgc90.pre import buildMesh2D
                x0 = cx - mp['lx'] / 2.0
                y0 = cy - mp['ly'] / 2.0
                surf = buildMesh2D(mp['mesh_type'], x0, y0,
                                   mp['lx'], mp['ly'], mp['nx'], mp['ny'])
                return pre.buildMeshedAvatar(mesh=surf, model=model_obj, material=material_obj)

            elif geom == "Boîte (H8)":
                from pylmgc90.pre import buildMeshH8
                x0 = cx - mp['lx'] / 2.0
                y0 = cy - mp['ly'] / 2.0
                z0 = cz - mp['lz'] / 2.0
                vol = buildMeshH8(x0, y0, z0,
                                  mp['lx'], mp['ly'], mp['lz'],
                                  mp['nx'], mp['ny'], mp['nz'])
                return pre.buildMeshedAvatar(mesh=vol, model=model_obj, material=material_obj)

            elif geom == "Disque":
                import tempfile, os
                from ..gui.dialogs.mesh_wiz_def import _gmsh_disk
                with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as f:
                    tmp = f.name
                try:
                    _gmsh_disk(cx, cy, mp['r'], mp['nr'], mp['ntheta'], tmp)
                    surf = pre.readMesh(tmp, 2)
                finally:
                    os.unlink(tmp)
                return pre.buildMeshedAvatar(mesh=surf, model=model_obj, material=material_obj)

            elif geom == "Sphère":
                import tempfile, os
                from ..gui.dialogs.mesh_wiz_def import _gmsh_sphere
                with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as f:
                    tmp = f.name
                try:
                    _gmsh_sphere(cx, cy, cz, mp['r'], mp['nr'], mp['ntheta'], mp['nphi'], tmp)
                    vol = pre.readMesh(tmp, 3)
                finally:
                    os.unlink(tmp)
                return pre.buildMeshedAvatar(mesh=vol, model=model_obj, material=material_obj)

            elif geom == "Cylindre":
                import tempfile, os
                from ..gui.dialogs.mesh_wiz_def import _gmsh_cylinder
                with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as f:
                    tmp = f.name
                try:
                    _gmsh_cylinder(cx, cy, cz, mp['r'], mp['h'],
                                   mp['nr'], mp['ntheta'], mp['nz'], tmp)
                    vol = pre.readMesh(tmp, 3)
                finally:
                    os.unlink(tmp)
                return pre.buildMeshedAvatar(mesh=vol, model=model_obj, material=material_obj)

            elif geom == "Fichier externe":
                filepath = mp.get('filepath', '')
                if not filepath:
                    raise ValueError("Chemin de fichier manquant pour MESH_DEFORMABLE externe.")
                mesh = pre.readMesh(filepath, dim)
                return pre.buildMeshedAvatar(mesh=mesh, model=model_obj, material=material_obj)

            else:
                raise ValueError(f"Géométrie MESH_DEFORMABLE inconnue : '{geom}'")

        
        else:
            raise ValueError(f"Type d'avatar non supporté: {atype}")

    # ── Création en masse depuis une ParticlePopulation (SoA) ────────────────

    @staticmethod
    def create_avatars_from_population(
        population: "ParticlePopulation", model_obj: Any, material_obj: Any
    ) -> List[Any]:
        """
        Crée les objets pylmgc90 réels pour toute une population, en une
        seule passe. Reste un appel Fortran par particule côté pylmgc90
        (limite structurelle de l'API : granulo_Random/depositInXxx sont
        vectorisés, mais la création d'avatar elle-même ne l'est pas),
        mais élimine tout l'overhead Python côté GUI (pas d'objet Avatar/
        dataclass intermédiaire par particule, accès direct aux arrays
        numpy de la population).

        Limité pour l'instant aux deux types que la génération granulo
        produit réellement : RIGID_DISK (2D) et RIGID_SPHERE (3D).
        """
        atype = population.avatar_type
        color = population.color
        centers = population.centers
        radii = population.radii
        extra = population.extra_params or {}

        bodies = []

        if atype == AvatarType.RIGID_DISK:
            for i in range(len(population)):
                bodies.append(pre.rigidDisk(
                    r=float(radii[i]),
                    center=centers[i],   # ndarray 1D — pylmgc90 accepte array-like
                    model=model_obj,
                    material=material_obj,
                    color=color,

                ))
    
        elif atype == AvatarType.RIGID_SPHERE:
            for i in range(len(population)):
                bodies.append(pre.rigidSphere(
                    r=float(radii[i]),
                    center=centers[i],   # ndarray 1D — pylmgc90 accepte array-like
                    model=model_obj,
                    material=material_obj,
                    color=color,
                ))
        elif atype == AvatarType.RIGID_DISCRETE:
            for i in range(len(population)):
                bodies.append(pre.rigidDiscreteDisk(
                    r=float(radii[i]), center=centers[i],
                    model=model_obj, material=material_obj, color=color,
                ))

        elif atype == AvatarType.RIGID_CLUSTER:
            nb_disk = int(extra.get('nb_disk', 3))
            for i in range(len(population)):
                bodies.append(pre.rigidCluster(
                    r=float(radii[i]), center=centers[i],
                    model=model_obj, material=material_obj, color=color,
                    nb_disk=nb_disk,
                ))

        elif atype == AvatarType.RIGID_CYLINDER:
            h = float(extra.get('h', 1.0))
            for i in range(len(population)):
                bodies.append(pre.rigidCylinder(
                    r=float(radii[i]), h=h, center=centers[i],
                    model=model_obj, material=material_obj, color=color,
                ))

        elif atype == AvatarType.RIGID_POLYGON:
            nb_vertices = int(extra.get('nb_vertices', 6))
            for i in range(len(population)):
                bodies.append(pre.rigidPolygon(
                    model=model_obj, material=material_obj, center=centers[i],
                    color=color, generation_type='regular',
                    nb_vertices=nb_vertices, radius=float(radii[i]),
                ))

        elif atype == AvatarType.RIGID_POLYHEDRON:
            nb_vertices = int(extra.get('nb_vertices', 8))
            for i in range(len(population)):
                bodies.append(pre.rigidPolyhedron(
                    nb_vertices=nb_vertices, vertices=None,
                    radius=float(radii[i]), generation_type='regular',
                    center=centers[i], model=model_obj, material=material_obj,
                    color=color, faces=None,
                ))

        else:
            raise ValueError(
                f"create_avatars_from_population : type non supporté "
                f"({atype.value}). Seuls RIGID_DISK/RIGID_SPHERE sont "
                f"couverts par ce chemin SoA pour l'instant."
            )

        return bodies

    @staticmethod
    def create_contact_law(law: ContactLaw) -> Any:
        """Crée une loi de contact pylmgc90"""
        lt   = law.law_type
        name = law.name
        p    = law.properties
        fric = law.friction

        # ── Rigide / Rigide ──────────────────────────────────────────────────

        if lt in (ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0):
            return pre.tact_behav(name=name, law=lt.value, fric=fric)
        if lt == ContactLawType.RST_CLB:
            return pre.tact_behav(
                name=name, law=lt.value,
                fric=fric,
                rstn=p.get('rstn', 0.0),
                rstt=p.get('rstt', 0.0)
            )

        elif lt == ContactLawType.IQS_DS_CLB:
            return pre.tact_behav(
                name=name, law=lt.value,
                fric=fric,
                stfr=p.get('stfr', 1e8),
                dyfr=p.get('dyfr', 1e8),
            )

        elif lt == ContactLawType.IQS_MOHR_DS_CLB:
            return pre.tact_behav(
                name=name, law=lt.value,
                fric=fric,
                stfr=p.get('stfr', 1e8),
                dyfr=p.get('dyfr', 1e8),
                cohn=p.get('cohn', 0.0),
                coht=p.get('coht', 0.0),
            )

        elif lt == ContactLawType.IQS_MAC_CZM:
            return pre.tact_behav(
                name=name, law=lt.value,
                stfr=p.get('stfr', 1e10),
                dyfr=p.get('dyfr', 1e10),
                cn=p.get('cn', 1e6),
                ct=p.get('ct', 1e6),
                b=p.get('b',  1.0),
                w=p.get('w',  0.01),
            )

        elif lt in (ContactLawType.GAP_SGR_CLB, ContactLawType.GAP_SGR_CLB_G0):
            return pre.tact_behav(name=name, law=lt.value, fric=fric)

        elif lt == ContactLawType.GAP_MOHR_DS_CLB:
            return pre.tact_behav(
                name=name, law=lt.value,
                fric=fric,
                stfr=p.get('stfr', 1e8),
                dyfr=p.get('dyfr', 1e8),
                cohn=p.get('cohn', 0.0),
                coht=p.get('coht', 0.0),
            )

        elif lt == ContactLawType.MAC_CZM:
            return pre.tact_behav(
                name=name, law=lt.value,
                stfr=p.get('stfr', 1e10),
                dyfr=p.get('dyfr', 1e10),
                cn=p.get('cn', 1e6),
                ct=p.get('ct', 1e6),
                b=p.get('b',  1.0),
                w=p.get('w',  0.01),
            )

        elif lt == ContactLawType.MAL_CZM:
            return pre.tact_behav(
                name=name, law=lt.value,
                stfr=p.get('stfr', 1e10),
                dyfr=p.get('dyfr', 1e10),
                cn=p.get('cn', 1e6),
                ct=p.get('ct', 1e6),
                s1=p.get('s1',  1.0),
                s2=p.get('s2',  1.0),
                G1=p.get('G1',  1.0),
                G2=p.get('G2',  1.0),
            )

        # ── Point / Point ─────────────────────────────────────────────────────

        elif lt == ContactLawType.ELASTIC_WIRE:
            return pre.tact_behav(
                name=name, law=lt.value,
                stiffness=p.get('stiffness', 1e6),
                prestrain=p.get('prestrain', 0.0),
            )

        elif lt == ContactLawType.BRITTLE_ELASTIC_WIRE:
            return pre.tact_behav(
                name=name, law=lt.value,
                stiffness=p.get('stiffness', 1e6),
                prestrain=p.get('prestrain', 0.0),
                Fmax=p.get('Fmax', 1e6),
            )

        elif lt == ContactLawType.ELASTIC_ROD:
            return pre.tact_behav(
                name=name, law=lt.value,
                stiffness=p.get('stiffness', 1e6),
                prestrain=p.get('prestrain', 0.0),
            )

        elif lt == ContactLawType.VOIGT_ROD:
            return pre.tact_behav(
                name=name, law=lt.value,
                stiffness=p.get('stiffness', 1e6),
                viscosity=p.get('viscosity', 1e3),
                prestrain=p.get('prestrain', 0.0),
            )

        # ── Any / Any ─────────────────────────────────────────────────────────

        elif lt in (ContactLawType.COUPLED_DOF, ContactLawType.NORMAL_COUPLED_DOF):
            return pre.tact_behav(name=name, law=lt.value)

        elif lt == ContactLawType.ELASTIC_REPELL_CLB:
            return pre.tact_behav(
                name=name, law=lt.value,
                fric=fric,
                stiffness=p.get('stiffness', 1e8),
            )

        else:
            raise ValueError(f"Type de loi non supporté : {lt}")

    
    @staticmethod
    def create_visibility_rule(rule: VisibilityRule, behavior_obj: Any) -> Any:
        """Crée une table de visibilité pylmgc90"""
        return pre.see_table(
            CorpsCandidat=rule.candidate_body,
            candidat=rule.candidate_contactor,
            colorCandidat=rule.candidate_color,
            CorpsAntagoniste=rule.antagonist_body,
            antagoniste=rule.antagonist_contactor,
            colorAntagoniste=rule.antagonist_color,
            behav=behavior_obj,
            alert=rule.alert
        )
    
    @staticmethod
    def apply_dof_operation(operation: DOFOperation, avatar_obj: Any) -> None:
        """
        Applique une opération DOF sur un avatar pylmgc90.
        
        Args:
            operation: Opération à appliquer
            avatar_obj: Objet avatar pylmgc90
        """
        getattr(avatar_obj, operation.operation_type)(**operation.parameters)