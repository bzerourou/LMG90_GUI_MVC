# Exemples fournis

Ce fichier rassemble un bref résumé des exemples disponibles dans `src/examples/`.
Chaque exemple est autonome : il construit un projet (matériaux, modèles, avatars,
lois de contact, tables de visibilité, opérations DOF, etc.) via une fonction
`build(controller)` et peut être chargé depuis l'interface **Examples** ou
exécuté en ouvrant le projet et en lançant le calcul.

Usage rapide
- Ouvrir l'application et choisir l'exemple via le menu *Exemples*.
- Ou exécuter `python main.py` et sélectionner l'exemple voulu.

Liste des exemples

---

## ex_avalanche_slope.py
Exemple avancé : avalanche granulaire sur pente inclinée.
- Mécanismes : mur incliné (rotation DOF), dépôt granulaire.
- Paramètres notables : `nb_particles=200`, pente à 25°.
- Notes : décalage du dépôt fait manuellement; utile pour tester écoulement.

---

## ex_biaxial_compression.py
Exemple avancé : essai de compression biaxiale sur un massif granulaire.
- Mécanismes : parois mobiles (roughWall + rotate DOF), granulo, DOF imposeDrivenDof.
- Paramètres notables : vitesse de compression, nb_particles=150.

---

## ex_cable_pendulum.py
Exemple avancé : pendule suspendu par câble.
- Mécanismes : contact point/point, loi `ELASTIC_WIRE`.
- Particularité : utilisation de `PT2Dx` pour points de câble; large `alert` pour la règle vis.

---

## ex_cluster_pile.py
Exemple avancé : empilement de clusters triangulaires (rigidCluster).
- Mécanismes : clusters (3 disques élémentaires), chute dans une boîte.
- Note : `rigidCluster` créé manuellement (non produit par generate_granulo).

---

## ex_cohesive_wall.py
Exemple : deux rangées de blocs liées par une loi cohésive (CZM).
- Mécanismes : brick2D + rigidBrick(), loi `IQS_MAC_CZM` avec propriétés passées via `properties`.
- Notes : montre configuration requise pour lois cohésives.

---

## ex_composite_scene.py
Exemple de synthèse — scène composite mélangeant tous les mécanismes.
- Mécanismes : disques, joncs, polygones, clusters, murs lisses/rouges, corps déformables, etc.
- Particularité : utilise `state.dynamic_vars` et `SafeEvaluator` pour paramètres réutilisables.
- Notes : long et pédagogique — bon point de départ pour tester l'ensemble des modules.

---

## ex_couette_shear.py
Exemple : dépôt granulométrique dans une cellule de Couette (anneau).
- Mécanismes : `Couette2D` container pour tester cisaillement annulaire.

---

## ex_deformable_drop.py
Exemple : corps déformable (maillage T3) chutant sur mur rigide.
- Mécanismes : maillage (`buildMesh2D`), `MESH_DEFORMABLE` avatar, interaction rigid/deformable.
- Notes : montre configuration de `Gap` laws et visibilité spécifiquement `MAILx` ↔ `RBDY2`.

---

## ex_deformable_impact.py
Exemple avancé : corps déformable avec contacteur `CLxxx` correctement câblé.
- Mécanismes : build mesh, `body.addContactors(...)`, `avatar.contactors`, `mesh_params['contactors']`.
- Usage : illustre les trois endroits à renseigner pour cohérence live / export / viewer.

---

## ex_dof_conditions.py
Exemple : conditions aux limites DOF — vitesse initiale et blocage de rotation.
- Mécanismes : `imposeInitValue`, `imposeDrivenDof` sur avatars individuels.

---

## ex_dumbbell_avatar.py
Exemple : avatar composite (haltère) construit via `EMPTY_AVATAR` + contacteurs.
- Mécanismes : combine `DISKx` + `JONCx` contactors dans un `emptyAvatar`.

---

## ex_for_loop_ramp.py
Exemple : boucle For générique — rampe de disques à rayon croissant.
- Mécanismes : `ForLoop` avec `template_config` évalué via `SafeEvaluator`.
- Utilité : montre la génération paramétrique d'avatars.

---

## ex_falling_disks.py
Exemple : chute de disques 2D sous gravité dans une boîte ouverte.
- Mécanismes : modèle de base pour tests de collisions et lois simples.

---

## ex_factory_injection.py
Exemple : Particle Factory — injection périodique de particules (batch).
- Mécanismes : `ParticleFactory`, configuration `FactoryConfig` et export `state.factories`.

---

## ex_granulo_deposit.py
Exemple : dépôt granulométrique par `granulo_Random` + `depositInBox2D`.
- Mécanismes : simple démonstration de génération granulo via `controller.generate_granulo()`.

---

## ex_hexagon_packing.py
Exemple : pavage hexagonal via `rigidPolygon` en mode `full`.
- Mécanismes : génération explicite de sommets pour un polygone régulier.

---

## ex_hopper_discharge.py
Exemple avancé : trémie (hopper) construite à partir de `roughWall` inclinés.
- Mécanismes : trémie + dépôt granulo, pattern des parois inclinées via rotation DOF.

---

## ex_l_shaped_wall.py
Exemple avancé : structure en L (deux murs de briques) recevant un dépôt granulométrique.
- Mécanismes : placement de briques via `pre.brick2D` + `rigidBrick` et groupes.

---

## ex_masonry_wall.py
Exemple : mur de maçonnerie en appareil Standard.
- Mécanismes : générateur de brique `pre.brick2D`, groupage et pattern Standard.

---

## ex_rotating_drum.py
Exemple avancé : tambour rotatif contenant un dépôt granulométrique.
- Mécanismes : `rigidDisk` creux (`is_hollow=True`) avec contacteur `xKSID`.

---

## ex_silo_factory.py
Exemple avancé : Particle Factory avec conteneur silo et lois complètes.
- Mécanismes : ParticleFactory, container `SILO_BOX`, postpro commands.

---

## ex_sphere_stack.py
Exemple : grille 3x3 de sphères rigides empilées sur un plan 3D.
- Mécanismes : démo 3D (RBDY3) — sphères et plan.

---

## ex_sphere_stack.py
(duplicata si présent) — voir le fichier source pour détails.

---

## Autres fichiers
- `src/examples/base.py` : base/utilitaires partagés pour les exemples (voir source).
- `src/examples/__init__.py` : export des exemples.

---

### Conseils pour intégrer dans la doc officielle
- Copier `docs/examples.md` dans votre documentation principale et ajouter un lien dans l'index.
- Indiquer les prérequis (e.g. pylmgc90 installé, vtk si besoin pour affichage 3D).
- Pour chaque exemple, mentionner les éventuelles limitations (contactor types, orientation des polygones, lois de contact avec propriétés requises).

---

Si vous voulez, je peux :
- Étendre chaque section avec un extrait de la signature `build(controller)` et paramètres modifiables, ou
- Générer des badges "Run"/"Open" pour chaque exemple, ou
- Produire une table d'index triée par mécanisme (granulo, déformable, 3D, factory, etc.).

Dites-moi le format souhaité ou si vous voulez que j'ajoute plus de détails par exemple (listes de paramètres modifiables, dépendances, etc.).
