# ============================================================================
# GranuloFastEngine — Moteur de génération granulométrique haute performance
# ============================================================================
"""
Génère des distributions granuloRandom en Python pur (numpy).
Objectif : 5 000 particules sans bloquer l'UI, sans pylmgc90 à la création.

Architecture :
  1. Calcul positions/rayons en numpy (thread séparé)
  2. Écriture directe DATBOX/BODIES.DAT (bypass pylmgc90)
  3. Peuplement de controller.state en batch unique (pas d'Avatar individuel)

Algorithme granuloRandom :
  - Placement aléatoire dans le conteneur
  - Détection collisions vectorisée (numpy broadcasting)
  - Rejet des positions invalides
  - Plusieurs passes jusqu'à atteindre le quota
"""

import numpy as np
import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
#  Structures de données légères (pas d'objets Avatar)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FastParticle:
    """Particule légère — juste les données géométriques"""
    center: List[float]
    radius: float


@dataclass
class FastGranuloResult:
    """Résultat d'une génération rapide"""
    particles: List[FastParticle]
    container_type: str
    container_params: Dict[str, float]
    radius_min: float
    radius_max: float
    material_name: str
    model_name: str
    avatar_type: str      # 'rigidDisk' ou 'rigidSphere'
    color: str
    group_name: str
    dimension: int
    nb_requested: int
    nb_generated: int
    seed: Optional[int]
    elapsed_seconds: float

    @property
    def success_rate(self) -> float:
        if self.nb_requested == 0:
            return 0.0
        return self.nb_generated / self.nb_requested * 100


# ─────────────────────────────────────────────────────────────────────────────
#  Moteur de calcul (numpy pur)
# ─────────────────────────────────────────────────────────────────────────────

class GranuloFastEngine:
    """
    Générateur haute performance pour la granuloRandom.

    Principe :
      - Génère des candidats en batch (numpy vectorisé)
      - Valide les collisions avec broadcasting O(n) au lieu de O(n²)
      - Émet une progression via callback

    Usage :
      engine = GranuloFastEngine()
      result = engine.generate(config, progress_callback=my_fn)
    """

    # Nombre maximum de tentatives par passe
    MAX_ATTEMPTS_FACTOR = 20
    # Taille des batches de candidats
    CANDIDATE_BATCH = 512

    def generate(
        self,
        nb_particles: int,
        radius_min: float,
        radius_max: float,
        container_type: str,
        container_params: Dict[str, float],
        material_name: str,
        model_name: str,
        avatar_type: str,
        color: str,
        group_name: str,
        dimension: int = 2,
        seed: Optional[int] = None,
        progress_callback=None,
    ) -> FastGranuloResult:
        """
        Génère nb_particles avatars dans le conteneur spécifié.

        progress_callback(current, total, message) — appelé régulièrement
        """
        t0 = time.perf_counter()

        rng = np.random.default_rng(seed)

        # Listes résultats (centres, rayons)
        centers = np.empty((0, dimension), dtype=np.float64)
        radii   = np.empty(0, dtype=np.float64)

        max_attempts = nb_particles * self.MAX_ATTEMPTS_FACTOR
        attempts = 0
        placed = 0

        # Marge de sécurité pour les bords (éviter les chevauchements avec les parois)
        wall_margin = radius_max

        # Récupérer les limites du conteneur
        bounds = self._get_bounds(container_type, container_params, dimension, wall_margin)

        if progress_callback:
            progress_callback(0, nb_particles, "Initialisation...")

        while placed < nb_particles and attempts < max_attempts:
            remaining = nb_particles - placed
            batch_size = min(self.CANDIDATE_BATCH, remaining * 4)

            # Générer des candidats aléatoires en batch
            candidate_radii   = rng.uniform(radius_min, radius_max, batch_size)
            candidate_centers = self._sample_in_container(
                rng, batch_size, container_type, container_params, dimension,
                candidate_radii
            )

            # Filtrer : hors conteneur
            valid_mask = self._check_in_container(
                candidate_centers, candidate_radii,
                container_type, container_params, dimension
            )

            candidate_centers = candidate_centers[valid_mask]
            candidate_radii   = candidate_radii[valid_mask]

            # Filtrer : collisions avec particules déjà placées
            if len(centers) > 0:
                no_collision = self._check_no_collision_batch(
                    candidate_centers, candidate_radii,
                    centers, radii, dimension
                )
                candidate_centers = candidate_centers[no_collision]
                candidate_radii   = candidate_radii[no_collision]

            # Accepter les candidats valides (en évitant les collisions entre eux)
            for i in range(len(candidate_centers)):
                if placed >= nb_particles:
                    break
                c = candidate_centers[i:i+1]
                r = candidate_radii[i]
                # Vérifier collision avec les déjà acceptés dans ce batch
                if len(centers) > 0:
                    ok = self._check_no_collision_single(c[0], r, centers, radii, dimension)
                    if not ok:
                        continue
                centers = np.vstack([centers, c]) if len(centers) > 0 else c
                radii   = np.append(radii, r)
                placed += 1

            attempts += batch_size

            if progress_callback and placed % max(1, nb_particles // 50) == 0:
                pct = placed / nb_particles
                elapsed = time.perf_counter() - t0
                rate = placed / elapsed if elapsed > 0 else 0
                eta = (nb_particles - placed) / rate if rate > 0 else 0
                progress_callback(
                    placed, nb_particles,
                    f"{placed}/{nb_particles} particules  |  {rate:.0f} part/s  |  ETA {eta:.1f}s"
                )

        if progress_callback:
            progress_callback(placed, nb_particles, f"Terminé : {placed} particules placées")

        elapsed = time.perf_counter() - t0

        # Convertir en FastParticle
        particles = [
            FastParticle(center=centers[i].tolist(), radius=float(radii[i]))
            for i in range(len(centers))
        ]

        return FastGranuloResult(
            particles=particles,
            container_type=container_type,
            container_params=container_params,
            radius_min=radius_min,
            radius_max=radius_max,
            material_name=material_name,
            model_name=model_name,
            avatar_type=avatar_type,
            color=color,
            group_name=group_name,
            dimension=dimension,
            nb_requested=nb_particles,
            nb_generated=len(particles),
            seed=seed,
            elapsed_seconds=elapsed,
        )

    # ── Géométrie conteneurs ──────────────────────────────────────────────────

    def _get_bounds(self, container_type, params, dim, margin):
        """Retourne les bornes AABB du conteneur (pour le sampling)"""
        if container_type == "Box2D":
            lx, ly = params['lx'], params['ly']
            return [(-lx/2 + margin, lx/2 - margin),
                    (-ly/2 + margin, ly/2 - margin)]
        elif container_type in ("Disk2D", "Drum2D"):
            r = params['r'] - margin
            return [(-r, r), (-r, r)]
        elif container_type == "Couette2D":
            rext = params['rext'] - margin
            return [(-rext, rext), (-rext, rext)]
        elif container_type == "Box3D":
            lx, ly, lz = params['lx'], params['ly'], params['lz']
            return [(-lx/2 + margin, lx/2 - margin),
                    (-ly/2 + margin, ly/2 - margin),
                    (-lz/2 + margin, lz/2 - margin)]
        elif container_type == "Sphere3D":
            r = params['r'] - margin
            return [(-r, r), (-r, r), (-r, r)]
        else:
            r = params.get('r', 2.0) - margin
            return [(-r, r), (-r, r)] + ([(-r, r)] if dim == 3 else [])

    def _sample_in_container(self, rng, n, container_type, params, dim, radii):
        """Génère n positions candidates uniformément dans le conteneur"""
        if container_type == "Box2D":
            lx, ly = params['lx'], params['ly']
            x = rng.uniform(-lx/2, lx/2, n)
            y = rng.uniform(-ly/2, ly/2, n)
            return np.column_stack([x, y])

        elif container_type in ("Disk2D", "Drum2D"):
            r = params['r']
            # Échantillonnage uniforme dans un disque
            theta = rng.uniform(0, 2*math.pi, n)
            rr    = r * np.sqrt(rng.uniform(0, 1, n))
            return np.column_stack([rr * np.cos(theta), rr * np.sin(theta)])

        elif container_type == "Couette2D":
            rint, rext = params['rint'], params['rext']
            theta = rng.uniform(0, 2*math.pi, n)
            # Uniforme dans la couronne
            rr = np.sqrt(rng.uniform(rint**2, rext**2, n))
            return np.column_stack([rr * np.cos(theta), rr * np.sin(theta)])

        elif container_type == "Box3D":
            lx = params.get('lx', 4.0)
            ly = params.get('ly', 4.0)
            lz = params.get('lz', 4.0)
            x = rng.uniform(-lx/2, lx/2, n)
            y = rng.uniform(-ly/2, ly/2, n)
            z = rng.uniform(-lz/2, lz/2, n)
            return np.column_stack([x, y, z])

        elif container_type == "Sphere3D":
            r = params['r']
            # Uniforme dans une sphère
            phi   = rng.uniform(0, 2*math.pi, n)
            costh = rng.uniform(-1, 1, n)
            sinth = np.sqrt(1 - costh**2)
            rr    = r * (rng.uniform(0, 1, n) ** (1/3))
            return np.column_stack([
                rr * sinth * np.cos(phi),
                rr * sinth * np.sin(phi),
                rr * costh
            ])

        else:
            # Fallback Box2D
            lx = params.get('lx', 4.0)
            ly = params.get('ly', 4.0)
            return np.column_stack([rng.uniform(-lx/2, lx/2, n),
                                    rng.uniform(-ly/2, ly/2, n)])

    def _check_in_container(self, centers, radii, container_type, params, dim):
        """Masque booléen : centres qui restent dans le conteneur (avec leur rayon)"""
        r = radii  # marge = rayon de la particule

        if container_type == "Box2D":
            lx, ly = params['lx'], params['ly']
            return (
                (centers[:, 0] - r >= -lx/2) & (centers[:, 0] + r <= lx/2) &
                (centers[:, 1] - r >= -ly/2) & (centers[:, 1] + r <= ly/2)
            )

        elif container_type in ("Disk2D", "Drum2D"):
            rmax = params['r']
            dist = np.linalg.norm(centers, axis=1)
            return dist + r <= rmax

        elif container_type == "Couette2D":
            rint, rext = params['rint'], params['rext']
            dist = np.linalg.norm(centers, axis=1)
            return (dist - r >= rint) & (dist + r <= rext)

        elif container_type == "Box3D":
            lx = params.get('lx', 4.0)
            ly = params.get('ly', 4.0)
            lz = params.get('lz', 4.0)
            return (
                (centers[:, 0] - r >= -lx/2) & (centers[:, 0] + r <= lx/2) &
                (centers[:, 1] - r >= -ly/2) & (centers[:, 1] + r <= ly/2) &
                (centers[:, 2] - r >= -lz/2) & (centers[:, 2] + r <= lz/2)
            )

        elif container_type == "Sphere3D":
            rmax = params['r']
            dist = np.linalg.norm(centers, axis=1)
            return dist + r <= rmax

        else:
            return np.ones(len(centers), dtype=bool)

    def _check_no_collision_batch(self, candidates, cand_radii, placed, placed_radii, dim):
        """
        Vectorisé : pour chaque candidat, vérifie qu'il ne chevauche aucun avatar placée.
        Returns masque booléen (True = pas de collision).
        """
        # candidates : (M, dim),  placed : (N, dim)
        # diff[i,j] = candidates[i] - placed[j]
        diff = candidates[:, np.newaxis, :] - placed[np.newaxis, :, :]   # (M, N, dim)
        dist2 = np.sum(diff**2, axis=2)                                   # (M, N)

        min_dist = cand_radii[:, np.newaxis] + placed_radii[np.newaxis, :]  # (M, N)
        min_dist2 = min_dist**2

        # Collision si dist2 < min_dist2 pour au moins un j
        collision = np.any(dist2 < min_dist2, axis=1)   # (M,)
        return ~collision

    def _check_no_collision_single(self, center, radius, placed, placed_radii, dim):
        """Vérifie qu'un avatar ne chevauche aucun avatar déjà placée."""
        diff  = placed - center
        dist2 = np.sum(diff**2, axis=1)
        min_dist2 = (placed_radii + radius)**2
        return not np.any(dist2 < min_dist2)


# ─────────────────────────────────────────────────────────────────────────────
#  Écriture fichier DATBOX
# ─────────────────────────────────────────────────────────────────────────────

class GranuloFileWriter:
    """
    Écrit les avatars directement dans DATBOX/BODIES.DAT
    au format LMGC90, en pylmgc90.

    Format BODIES.DAT (rigidDisk 2D) :
      $bdyty
      RBDY2
      $blmty
      DISKx  behav=MAT001  color=BLUEx
               0.100000D+00
      $coor
               0.000000D+00   0.000000D+00
      $angle
               0.000000D+00
      $vel
               0.000000D+00   0.000000D+00   0.000000D+00
      $$
    """

    def write(self, result: FastGranuloResult, output_dir: Path) -> Path:
        """
        Écrit les particules dans output_dir/BODIES.DAT
        Retourne le chemin du fichier écrit.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "BODIES.DAT"

        lines = []

        if result.dimension == 2:
            lines += self._write_2d(result)
        else:
            lines += self._write_3d(result)

        filepath.write_text("\n".join(lines) + "\n", encoding="ascii")
        return filepath

    def _write_2d(self, result: FastGranuloResult) -> List[str]:
        lines = []
        mat  = result.material_name.upper().ljust(6)[:6]
        col  = result.color.ljust(5)[:5]

        for p in result.particles:
            cx, cy = p.center[0], p.center[1]
            r = p.radius
            lines += [
                "$bdyty",
                "RBDY2",
                "$blmty",
                f"DISKx  behav={mat}  color={col}",
                f"  {r:20.12E}",
                "$coor",
                f"  {cx:20.12E}  {cy:20.12E}",
                "$angle",
                f"  {0.0:20.12E}",
                "$vel",
                f"  {0.0:20.12E}  {0.0:20.12E}  {0.0:20.12E}",
                "$$",
            ]
        return lines

    def _write_3d(self, result: FastGranuloResult) -> List[str]:
        lines = []
        mat = result.material_name.upper().ljust(6)[:6]
        col = result.color.ljust(5)[:5]

        for p in result.particles:
            cx, cy, cz = p.center[0], p.center[1], p.center[2]
            r = p.radius
            lines += [
                "$bdyty",
                "RBDY3",
                "$blmty",
                f"SPHER  behav={mat}  color={col}",
                f"  {r:20.12E}",
                "$coor",
                f"  {cx:20.12E}  {cy:20.12E}  {cz:20.12E}",
                "$angle",
                f"  {1.0:20.12E}  {0.0:20.12E}  {0.0:20.12E}  {0.0:20.12E}",
                "$vel",
                (f"  {0.0:20.12E}  {0.0:20.12E}  {0.0:20.12E}"
                 f"  {0.0:20.12E}  {0.0:20.12E}  {0.0:20.12E}"),
                "$$",
            ]
        return lines


# ─────────────────────────────────────────────────────────────────────────────
#  Intégration controller.state (batch unique)
# ─────────────────────────────────────────────────────────────────────────────

class GranuloStateIntegrator:
    """
    Intègre le résultat dans controller.state en une seule opération.
    N'utilise pas add_avatar() — écrit directement dans state.avatars
    via un batch numpy pour éviter 5000 appels avatars.
    """

    def integrate(self, result: FastGranuloResult, controller) -> List[int]:
        """
        Ajoute les avatars à controller.state et à _bodies_container
        (requis pour pre.visuAvatars).
        Retourne la liste des indices créés.
        """
        from ..core.models import Avatar, AvatarType, AvatarOrigin, GranuloGeneration
        from ..core.pylmgc_bridge import LMGC90Bridge

        start_idx = len(controller.state.avatars)
        avatar_type = AvatarType(result.avatar_type)

        # Récupérer mat/mod pylmgc90 une seule fois
        mat_obj = controller._pylmgc_materials.get(result.material_name)
        mod_obj = controller._pylmgc_models.get(result.model_name)

        if not mat_obj:
            raise ValueError(
                f"Matériau pylmgc90 '{result.material_name}' introuvable. "
                "Créez-le d'abord via l'onglet Matériaux."
            )
        if not mod_obj:
            raise ValueError(
                f"Modèle pylmgc90 '{result.model_name}' introuvable. "
                "Créez-le d'abord via l'onglet Modèles."
            )

        new_avatars = []
        for idx_p, p in enumerate(result.particles):
            # pylmgc90 attend un np.array pour center (pas une liste Python)
            center_np = np.array(p.center, dtype=float)

            av = Avatar(
                avatar_type=avatar_type,
                center=center_np,       # np.array pour le bridge
                material_name=result.material_name,
                model_name=result.model_name,
                color=result.color,
                origin=AvatarOrigin.GRANULO,
                radius=p.radius,
            )

            try:
                body_obj = LMGC90Bridge.create_avatar(av, mod_obj, mat_obj)
            except Exception as e:
                raise ValueError(
                    f"Erreur pylmgc90 sur l'avatar #{idx_p} "
                    f"(center={p.center}, r={p.radius:.4f}) : {e}"
                )

            controller._bodies_container.addAvatar(body_obj)
            controller._pylmgc_bodies.append(body_obj)

            # Stocker avec tolist() pour la sérialisation JSON
            av.center = center_np.tolist()
            new_avatars.append(av)

        # Batch unique dans state
        controller.state.avatars.extend(new_avatars)
        idx = list(range(start_idx, start_idx + len(new_avatars)))

        # generated_avatar_ids.
        generated_avatar_ids = [
            controller.state.avatars[i].avatar_id for i in idx
        ]

        # Groupe
        if result.group_name:
            grp = controller.state.avatar_groups
            if result.group_name not in grp:
                grp[result.group_name] = []
            grp[result.group_name].extend(generated_avatar_ids)

        # GranuloGeneration
        gen = GranuloGeneration(
            nb_particles=result.nb_requested,
            radius_min=result.radius_min,
            radius_max=result.radius_max,
            container_type=result.container_type,
            container_params=result.container_params,
            model_name=result.model_name,
            material_name=result.material_name,
            avatar_type=result.avatar_type,
            color=result.color,
            seed=result.seed,
            group_name=result.group_name,
            generated_ids=generated_avatar_ids,
        )
        controller.state.granulo_generations.append(gen)

        # Un seul signal à la fin
        controller.state_changed.emit()

        return idx