# LMGC90_GUI — Bibliothèque d'exemples

> Documentation de quelques exemples fournis avec l'application, accessibles via
> **📚 Exemples → Parcourir les exemples...** (`Ctrl+Shift+E`).


![exemples fournis](../captures/biblio_exemples.png)

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Bases](#2-bases)
   - [Chute de disques 2D](#21-chute-de-disques-2d)
   - [Empilement de sphères 3D](#22-empilement-de-sphères-3d)
3. [Structures](#3-structures)
   - [Mur de maçonnerie](#31-mur-de-maçonnerie)
   - [Mur avec liaisons cohésives (CZM)](#32-mur-avec-liaisons-cohésives-czm)
4. [Génération de masse](#4-génération-de-masse)
   - [Dépôt granulométrique](#41-dépôt-granulométrique)
   - [Boucle géométrique — Cercle](#42-boucle-géométrique--cercle)
5. [Avancé — Contact et mécanismes](#5-avancé--contact-et-mécanismes)
   - [Tambour rotatif](#51-tambour-rotatif)
   - [Décharge en trémie](#52-décharge-en-trémie)
   - [Contact roue/rail (ferroviaire)](#53-contact-roueRail-ferroviaire)
   - [Frein à disque de vélo](#54-frein-à-disque-de-vélo)
   - [Roulement à billes (coupe 2D)](#55-roulement-à-billes-coupe-2d)
6. [Avancé — Déformable](#6-avancé--déformable)
   - [Corps déformable sur sol rigide](#61-corps-déformable-sur-sol-rigide)
7. [Synthèse](#7-synthèse)
   - [Scène composite](#71-scène-composite)
8. [Tableau récapitulatif complet](#8-tableau-récapitulatif-complet)

---

## 1. Vue d'ensemble côté dev

Chaque exemple est une **fonction `build(controller)`** qui reçoit un
`ProjectController` fraîchement créé et le peuple entièrement via l'API
publique du contrôleur (`add_material`, `add_avatar`, `generate_loop`,
`add_dof_operation`, ...). Ce choix — code plutôt que fichier `.lmgc90`
statique — garantit que chaque exemple reste valide indéfiniment : il suit
automatiquement toute évolution du schéma de données du projet.

Les exemples sont déclarés dans `src/examples/__init__.py` sous forme de
`ExampleSpec` :

```python
ExampleSpec(
    id="falling_disks",       # identifiant stable
    title="🎱 Chute de disques 2D",
    category="Bases",         # regroupement dans ExamplesDialog
    description="...",        # HTML autorisé
    dimension=2,               # 2 ou 3, informatif
    difficulty="Débutant",    # Débutant | Intermédiaire | Avancé
    builder=_build_falling_disks,
    tags=["avatar", "contact", "boucle"],
)
```

Chargement d'un exemple : `MainWindow._on_browse_examples()` crée un
nouveau projet vide (`controller.new_project(title)`) puis appelle
`example.builder(controller)`.

---

## 2. Bases

### 2.1 Chute de disques 2D

**Fichier :** `src/examples/ex_falling_disks.py` · **ID :** `falling_disks`
**Dimension :** 2D · **Difficulté :** Débutant

Le point de départ classique : une rangée de disques rigides tombe sous
gravité sur un mur.

| Élément | Détail |
|---|---|
| Matériau | `TDURx`, RIGID, ρ = 2500 kg/m³ |
| Modèle | `rigid`, MECAx / Rxx2D |
| Sol | `SMOOTH_WALL` (mur lisse fixe), `l=4.0`, `h=0.1` |
| Avatars mobiles | 10 `RIGID_DISK` (r = 0.1 m) via boucle **Ligne** (`step=0.3`) |
| Loi de contact | `IQS_CLB`, friction = 0.3 |
| Visibilité | Disque/Disque + Disque/Sol (contacteurs `DISKx`/`JONCx`) |

**Mécanismes illustrés :** `Loop` géométrique de type Ligne, création d'un
avatar modèle puis génération automatique des copies via
`controller.generate_loop(loop)`.

---

### 2.2 Empilement de sphères 3D

**Fichier :** `src/examples/ex_sphere_stack.py` · **ID :** `sphere_stack`
**Dimension :** 3D · **Difficulté :** Débutant

Grille 3×3 de sphères rigides empilées sur un plan.

| Élément | Détail |
|---|---|
| Matériau | `TDURx`, RIGID, ρ = 2500 kg/m³ |
| Modèle | `rigid`, MECAx / Rxx3D |
| Sol | `RIGID_PLAN` (`axe1=axe2=2.0`, `axe3=0.05`) |
| Avatars | 9 `RIGID_SPHERE` (r = 0.15 m), grille 3×3, pas = 0.6 m |
| Lois | `IQS_CLB`, friction = 0.3 |
| Visibilité | Sphère/Sphère + Sphère/Plan (`SPHER`/`PLANx`) |

**Note d'implémentation :** placement **direct** des sphères (boucle
Python `for`), car le générateur `Loop` "Grille" intégré ne produit que
des centres 2D — voir `core/generators.py::LoopGenerator.generate_grid`.

---

## 3. Structures

### 3.1 Mur de maçonnerie

**Fichier :** `src/examples/ex_masonry_wall.py` · **ID :** `masonry_wall`
**Dimension :** 2D · **Difficulté :** Intermédiaire

Mur de 8 rangs × 5 colonnes de briques en appareil **Standard**
(décalage d'une demi-brique entre rangs consécutifs).

| Élément | Détail |
|---|---|
| Matériau | `brick`, RIGID, ρ = 1800 kg/m³ |
| Brique | `pre.brick2D("std", lx=0.20, ly=0.065)` (dimension française standard) |
| Représentation | `EMPTY_AVATAR` avec `wall_params={'l','h','brick_name'}` |
| Groupe | `mur_briques` (tous les avatars générés) |
| Loi de contact | `IQS_CLB`, friction = 0.6 |

**Mécanisme clé :** chaque brique est créée en deux temps — objet
pylmgc90 réel via `pre.brick2D(...).rigidBrick(...)` (ajouté directement
à `controller._bodies_container`), puis un `Avatar(EMPTY_AVATAR)`
correspondant dans `state.avatars` pour la persistance/l'UI.

---

### 3.2 Mur avec liaisons cohésives (CZM)

**Fichier :** `src/examples/ex_cohesive_wall.py` · **ID :** `cohesive_wall`
**Dimension :** 2D · **Difficulté :** Avancé

Deux rangées de 6 blocs collées avec une loi de **zone cohésive**
(résistance avant rupture, puis dégradation).

| Élément | Détail |
|---|---|
| Brique | 0.25 × 0.10 m, 2 assises × 6 colonnes |
| Loi de contact | `IQS_MAC_CZM` |
| Propriétés obligatoires | `stfr=1e10`, `dyfr=1e10`, `cn=5e6`, `ct=3e6`, `b=1.0`, `w=0.02` |

**Point d'attention documenté dans le code source :** les propriétés
`IQS_MAC_CZM` doivent être passées via `properties={...}` et **jamais**
comme paramètres directs du constructeur `ContactLaw` (piège déjà
rencontré et corrigé dans `ex_deformable_drop.py`).

---

## 4. Génération de masse

### 4.1 Dépôt granulométrique

**Fichier :** `src/examples/ex_granulo_deposit.py` · **ID :** `granulo_deposit`
**Dimension :** 2D · **Difficulté :** Intermédiaire

500 disques de rayons aléatoires déposés par gravité dans une boîte.

| Paramètre | Valeur |
|---|---|
| Nombre de particules | 500 |
| Rayons | [0.03, 0.08] m |
| Conteneur | `Box2D`, `lx=4.0`, `ly=4.0` |
| Seed | 42 (reproductible) |
| Groupe | `depot_box` |

**API illustrée :** `GranuloGeneration` + `controller.generate_granulo(config)`
— appelle en interne `pre.granulo_Random` puis `pre.depositInBox2D` (voir
`core/generators.py::GranuloGenerator`).

---

### 4.2 Boucle géométrique — Cercle

**Fichier :** `src/examples/ex_circle_loop.py` · **ID :** `circle_loop`
**Dimension :** 2D · **Difficulté :** Débutant

12 disques disposés en cercle (rayon 2.0 m) autour d'un avatar modèle.

**Mécanisme :** création d'un `Avatar` modèle (`ORANx`, r = 0.15 m), puis
`Loop(loop_type="Cercle", model_avatar_id=..., count=12, radius=2.0)` →
`controller.generate_loop(loop)`. Illustre le pattern **avatar modèle +
boucle géométrique**, réutilisé par `LoopTab` dans l'UI.

---

## 5. Avancé — Contact et mécanismes

### 5.1 Tambour rotatif

**Fichier :** `src/examples/ex_rotating_drum.py` · **ID :** `rotating_drum`
**Dimension :** 2D · **Difficulté :** Avancé

Disque creux (`is_hollow=True`) entraîné en rotation constante, contenant
un dépôt granulométrique.

| Élément | Détail |
|---|---|
| Tambour | `RIGID_DISK`, r = 2.2 m, `is_hollow=True` → contacteur `xKSID` |
| DOF tambour | translation bloquée (`component=[1,2]`) + rotation entraînée (`component=3, ct=0.5 rad/s`) |
| Dépôt interne | `Drum2D`, r = 2.0 m (< rayon tambour), 200 particules, [0.05, 0.09] m |
| Loi | `IQS_CLB`, friction = 0.45 |
| Post-pro | `COORDINATION NUMBER` |

**Point clé :** le contacteur `xKSID` (paroi cylindrique **intérieure**)
est le même mécanisme que celui utilisé par le conteneur `Drum2D` de la
génération granulométrique standard — voir aussi
[Roulement à billes](#55-roulement-à-billes-coupe-2d) qui réutilise ce
même principe pour la bague extérieure.

---

### 5.2 Décharge en trémie

**Fichier :** `src/examples/ex_hopper_discharge.py` · **ID :** `hopper_discharge`
**Dimension :** 2D · **Difficulté :** Avancé

Trémie en V construite à partir de deux `roughWall` inclinés, recevant un
dépôt granulométrique de 180 disques.

| Élément | Détail |
|---|---|
| Géométrie trémie | `top_width=1.6`, `bottom_width=0.45`, `height=1.2` m |
| Parois | 2× `ROUGH_WALL` + rotation `DOFOperation(operation_type="rotate", ...)` autour du centre propre du mur |
| Immobilisation | `imposeDrivenDof` de **groupe** (`hopper_walls`) |
| Dépôt | `Box2D`, 180 particules, [0.04, 0.07] m |
| Post-pro | `KINETIC ENERGY` |

**Note historique documentée dans le code :** la première version
utilisait `AvatarFactory.create_hopper_2d()`, abandonnée car
`computeRigidProperties()` échouait (incohérence radius/vertices).
Reconstruite avec le pattern **roughWall + rotation DOF**, validé et
réutilisé ensuite dans `particle_factory.py` pour les parois de
conteneur.

---

### 5.3 Contact roue/rail (ferroviaire)

**Fichier :** `src/examples/ex_wheel_rail_contact.py` · **ID :** `wheel_rail_contact`
**Dimension :** 3D · **Difficulté :** Avancé

Roue cylindrique roulant sur un rail modélisé en plan rigide, avec un
tronçon de **joint de rail** présentant un léger défaut d'alignement.

| Élément | Détail |
|---|---|
| Roue | `RIGID_CYLINDER`, Ø 920 mm (norme UIC), largeur bandage 135 mm |
| Rail | `RIGID_PLAN`, longueur 3.0 m, champignon 70 mm |
| Joint de rail | second `RIGID_PLAN`, défaut vertical de 4 mm |
| DOF roue | guidage latéral bloqué (`component=2`) + translation longitudinale imposée (`component=1, ct=1.5 m/s`) |
| DOF rail/joint | totalement immobilisés (6 DDL RBDY3) |
| Loi roulement | `IQS_CLB`, friction = 0.3 (acier/acier sec) |
| Loi impact joint | `RST_CLB`, friction = 0.2, `rstn=0.3`, `rstt=0.15` |
| Post-pro | `KINETIC ENERGY`, `TORQUE EVOLUTION` (sur la roue) |

**Mécanismes illustrés :** deux lois de contact **distinctes** appliquées
au même couple de types de contacteurs (`CYLND`/`PLANx`) selon la couleur
de l'antagoniste — permet de représenter un comportement différencié
(roulement continu vs impact localisé) sans dupliquer les avatars.

---

### 5.4 Frein à disque de vélo

**Fichier :** `src/examples/ex_disc_brake.py` · **ID :** `disc_brake`
**Dimension :** 3D · **Difficulté :** Avancé

Disque de frein serré par deux plaquettes d'étrier ; c'est le frottement
qui freine réellement la roue.

| Élément | Détail |
|---|---|
| Disque | `RIGID_CYLINDER`, Ø 160 mm, épaisseur 1.8 mm |
| Plaquettes | 2× `RIGID_PLAN`, 34 × 20 × 8 mm, fermeture du piston à 5 mm/s |
| Moyeu | translation + tangage/lacet bloqués, **rotation propre libre** |
| Condition initiale | `imposeInitValue(component=6, value=ω₀)` — roue à 25 km/h |
| Loi de contact | `IQS_CLB`, friction = 0.40 (semi-métallique / inox à sec) |
| Post-pro | `KINETIC ENERGY`, `DISSIPATED ENERGY`, `TORQUE EVOLUTION` |

**Point de fidélité physique :** contrairement à un simple entraînement,
la rotation du disque est posée comme **condition initiale**
(`imposeInitValue`) et non comme vitesse imposée en continu
(`imposeDrivenDof`) — sans cela, le frottement des plaquettes n'aurait
aucun effet observable et l'exemple ne représenterait pas un freinage.

---

### 5.5 Roulement à billes (coupe 2D)

**Fichier :** `src/examples/ex_ball_bearing.py` · **ID :** `ball_bearing`
**Dimension :** 2D · **Difficulté :** Avancé

Coupe transversale d'un roulement rainuré à billes type 608.

| Élément | Détail |
|---|---|
| Bague extérieure | `RIGID_DISK` creux (`is_hollow=True`), r ≈ 9.5 mm, fixe |
| Bague intérieure | `RIGID_DISK` plein, r ≈ 5.0 mm, rotation pure entraînée (~300 tr/min) |
| Billes | 7× `RIGID_DISK` libres (**aucun DOF imposé**), calées dans l'entrefer |
| Loi | `IQS_CLB`, friction = 0.05 (roulement lubrifié) |
| Post-pro | `KINETIC ENERGY`, `COORDINATION NUMBER`, `VIOLATION EVOLUTION` |

**Limitation documentée :** LMGC90_GUI ne supporte les disques creux
(`is_hollow`) qu'en 2D — le roulement est donc représenté en coupe
transversale plutôt qu'en 3D torique complet (même contrainte que
[Tambour rotatif](#51-tambour-rotatif)). Les billes ne reçoivent aucune
vitesse imposée : leur mouvement résulte uniquement du contact avec les
deux pistes, cohérent avec le principe physique d'un roulement réel.

---

## 6. Avancé — Déformable

### 6.1 Corps déformable sur sol rigide

**Fichier :** `src/examples/ex_deformable_drop.py` · **ID :** `deformable_drop`
**Dimension :** 2D · **Difficulté :** Avancé

Rectangle déformable (maillage triangulaire, matériau élastique) chutant
sur un mur rigide.

| Élément | Détail |
|---|---|
| Matériau déformable | `ELAS1`, ELAS, young=70 GPa, ν=0.3 |
| Maillage | `pre.buildMesh2D("2T3", ...)`, 6×3 éléments, rectangle 1.0×0.4 m |
| Modèle EF | `femxx`, élément `T3xxx` |
| Sol | `SMOOTH_WALL` rigide |
| Loi | `GAP_SGR_CLB`, friction = 0.3 (rigide/déformable) |

**Voir aussi :** `ex_deformable_impact.py` (câblage complet du
contacteur `CLxxx` via `addContactors`, indispensable au contact réel —
la simplification de cet exemple-ci ne suffit pas pour un calcul avec
contact fonctionnel).

---

## 7. Synthèse

### 7.1 Scène composite

**Fichier :** `src/examples/ex_composite_scene.py` · **ID :** `composite_scene`
**Dimension :** 2D · **Difficulté :** Avancé

L'exemple le plus complet du registre : combine presque tous les
mécanismes dans un seul projet.

| Catégorie | Contenu |
|---|---|
| Avatars | disque, jonc, polygone (losange), cluster, mur de briques, rampe inclinée |
| Matériaux | 3 (`brick`, `TDURx`, `steel`), densités différentes |
| Lois de contact | `IQS_CLB` (frottement pur), `RST_CLB` (restitution), `IQS_MOHR_DS_CLB` (cohésion + frottement) |
| Visibilité | tables croisées **par paire de couleurs** (pas seulement même-couleur) |
| Variables dynamiques | 11 variables interdépendantes (`state.dynamic_vars`), consultables via **Outils → Variables dynamiques** après chargement |

**Intérêt pédagogique :** montre comment les variables dynamiques
peuvent piloter toute la géométrie d'une scène (`site_width`,
`joint_thickness`, `disk_spacing = disk_radius * spacing_factor`, ...),
en réutilisant `SafeEvaluator` / `build_eval_context` exactement comme le
ferait un champ de formulaire dans l'UI.

---

## 8. Tableau récapitulatif complet

| ID | Titre | Dim. | Difficulté | Tags principaux |
|---|---|:-:|---|---|
| `falling_disks` | Chute de disques 2D | 2D | Débutant | avatar, contact, boucle |
| `sphere_stack` | Empilement de sphères 3D | 3D | Débutant | avatar, 3d |
| `masonry_wall` | Mur de maçonnerie | 2D | Intermédiaire | maconnerie, groupe |
| `granulo_deposit` | Dépôt granulométrique | 2D | Intermédiaire | granulo, masse |
| `circle_loop` | Boucle géométrique — Cercle | 2D | Débutant | boucle, groupe |
| `deformable_drop` | Corps déformable sur sol rigide | 2D | Avancé | deformable, fem |
| `cohesive_wall` | Mur avec liaisons cohésives (CZM) | 2D | Avancé | contact, czm |
| `dumbbell_avatar` | Avatar composite — haltère | 2D | Intermédiaire | avatar_vide, contacteurs |
| `for_loop_ramp` | Boucle For — rampe de rayons | 2D | Intermédiaire | boucle, for |
| `dof_conditions` | Conditions aux limites DOF | 2D | Intermédiaire | dof, conditions_limites |
| `couette_shear` | Cisaillement en cellule de Couette | 2D | Avancé | granulo, couette |
| `hopper_discharge` | Décharge en trémie | 2D | Avancé | factory, granulo, dof |
| `cable_pendulum` | Pendule à câble | 2D | Avancé | contact, dof, point_point |
| `deformable_impact` | Impact déformable (contacteur complet) | 2D | Avancé | deformable, contact |
| `l_shaped_wall` | Structure en L + granulo | 2D | Avancé | maconnerie, granulo, dof |
| `silo_factory` | Factory en silo | 2D | Avancé | factory, contact, postpro |
| `rotating_drum` | Tambour rotatif | 2D | Avancé | dof, granulo, rotation |
| `biaxial_compression` | Compression biaxiale | 2D | Avancé | dof, granulo, essai_mecanique |
| `hexagon_packing` | Pavage hexagonal | 2D | Intermédiaire | avatar, polygone |
| `cluster_pile` | Empilement de clusters | 2D | Intermédiaire | avatar, cluster |
| `avalanche_slope` | Avalanche sur pente inclinée | 2D | Avancé | dof, granulo, pente |
| `wheel_rail_contact` | Contact roue/rail (ferroviaire) | 3D | Avancé | contact, 3d, ferroviaire, dof, postpro |
| `disc_brake` | Frein à disque de vélo | 3D | Avancé | contact, 3d, frein, dof, postpro, energie |
| `ball_bearing` | Roulement à billes (coupe 2D) | 2D | Avancé | contact, roulement, dof, postpro |
| `composite_scene` | Scène composite — synthèse complète | 2D | Avancé | synthese, variables, contact, avatar |

---

## Annexe — Ajouter un nouvel exemple

1. Créer `src/examples/ex_mon_exemple.py` avec une fonction
   `build(controller) -> None`.
2. Peupler le projet **uniquement** via l'API publique du contrôleur
   (`add_material`, `add_model`, `add_avatar`, `generate_loop`,
   `generate_granulo`, `add_contact_law`, `add_visibility_rule`,
   `add_dof_operation`, `add_postpro_command`, ...) — jamais d'accès
   direct aux structures internes sauf si un exemple existant le
   justifie explicitement (ex. `pre.brick2D` pour la maçonnerie).
3. Terminer par `controller.state.name = "Exemple - ..."`.
4. Dans `src/examples/__init__.py` :
   - importer `build as _build_mon_exemple` ;
   - ajouter une entrée `ExampleSpec(...)` dans la liste `EXAMPLES`.
5. Documenter l'exemple dans ce fichier (`exemples.md`), en suivant le
   format des sections ci-dessus : tableau de paramètres, mécanismes
   illustrés, points de fidélité physique ou limitations connues.