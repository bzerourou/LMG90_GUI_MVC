# Onglet Calcul LMGC90_GUI

## Vue d'ensemble

L'onglet `calcul` gère la configuration et le lancement des simulations LMGC90. Il génère automatiquement le DATBOX et le script `command.py`, puis exécute ce script.
## Paramètres de calcul

![](captures/calcul.JPG)

| Paramètre | Champ UI | Valeur par défaut | Description |
|---|---|---|---|
| `dt` | Pas de temps | `1e-3` | Incrément temporel |
| `nb_steps` | Nombre d'itérations | `1000` | Nombre de pas de calcul |
| `theta` | Theta intégrateur | `0.5` | Paramètre du schéma d'intégration |
| `tol` | Tolérance | `1.666e-4` | Tolérance de convergence du solveur |
| `relax` | Relaxation | `1.0` | Facteur de relaxation |
| `norm` | Norme | `Quad ` | Norme de convergence (`Quad `, `QM   `, `Maxim`) |
| `gs_it1` | Itérations GS1 | `50` | Nombre d'itérations Gauss-Seidel (boucle externe) |
| `gs_it2` | Itérations GS2 | `100` | Nombre d'itérations Gauss-Seidel (boucle interne) |
| `solver_type` | Solveur | `NLGS` | Type de solveur (`Stored_Delassus_Loops`, `Exchange_Local_Global`, `Exchange_Local_Global` ) |
| `freq_write` | Fréquence écriture | `50` | Écriture des résultats tous les N pas |
| `freq_display` | Fréquence affichage | `50` | Mise à jour affichage tous les N pas |


## Fichiers générés au lancement d'un calcul

| Fichier | Emplacement | Description |
|---|---|---|
| `DATBOX/` | Dossier du projet | Données d'entrée LMGC90 |
| `command.py` | Dossier du projet | Script de calcul chipy |
| `OUTBOX/` | Dossier du projet | Résultats (créé par LMGC90) |
| `Display/` | Dossier du projet | Fichiers d'affichage |
| `Postpro/` | Dossier du projet | Fichiers post-traitement |


### Paramétrer vos calculs 
Il est possible de paramétrer vos scripts calculs via au bouton "Configurer les routines chipy", une boite de dialogue s'ouvrira sur votre interface, 

![](captures/config_calculs.JPG)

#### 1.Onglet Modèle 
Le premier onglet fait l'objet d'une détéection automatique sur l'hypothèse de votre modèle, et charge tous les paramètres se lon vos avatars, 

|Contraintes planes (mhyp = 1)	|Calcul 2D en état plan de contraintes. Pertinent pour les structures minces.
| --- | ------- |
|Déformations planes (mhyp = 2)	|Calcul 2D en état plan de déformations. Pertinent pour les structures infiniment longues en z.|
|Tridimensionnel (mhyp = 3)	|Calcul 3D complet.|

##### Corps déformables 
|Activer les corps déformables	|Génère ReadDatbox(deformable=True) dans le script. Active automatiquement mecaFEMx si la physique est MECAx.|
|----|--------|
|Physique FEM	|Détermine le solveur éléments finis utilisé : MECAx (mécanique des solides), THERx (thermique), HYDRx (hydraulique), ou THMx (thermo-hydraulique-mécanique couplé).|
|Rloc_tol	|Tolérance sur les efforts de contact pour la reprise de Rloc. Valeur typique : 5 × 10⁻². Utilisée dans chipy.SetRlocTol().|


#### 2.Routines
Cet onglet sélectionne les routines chipy à inclure dans la boucle de calcul. Chaque case à cocher correspond à un appel de la famille NewStep / ComputeStep / WriteOut dans le script généré.

**Corps rigides 2D — RBDY2**

–	RBDY2 (NewStep / FreeVelocity / WriteOut) — coché par défaut. Routines obligatoires pour tout corps rigide 2D. Génère RBDY2_NewStep(), RBDY2_FreeVelocity(), RBDY2_WriteOut() dans la boucle.

**Corps rigides 3D — RBDY3**

–	RBDY3 (NewStep / FreeVelocity / WriteOut) — déclenche les routines équivalentes en 3D.

**Détecteurs de contact 2D**

Chaque case active la détection de contact entre une paire de types de contacteurs. Le script génère XXX_SelectProxTactors() et XXX_RecupRloc() / XXX_StockRloc() correspondants.
|Détecteur	|Description|
|---|-----|
|`DKDKx`	|Disque / Disque (coché par défaut) — granulométrie 2D, milieux granulaires|
|`DKJCx`	|Disque / Jonc — particules avec ellipses|
|`DKKDx`	|Disque / Polygone (Corde) — interaction disque-paroi polygonale|
|`PLPLx`	|Plan / Plan — parois planes entre elles|
|`CLALp`	|Ligne / Ligne maçonnerie — interfaces entre briques (CLALp)|
|`ALpALp`	|Ligne / Ligne ALp — variante pour contacteurs polygonaux|

**Détecteurs de contact 3D**
|Détecteur	|Description|
|---|-----|
|SPSPx	|Sphère / Sphère — granulométrie 3D|
|SPCDx	|Sphère / Cylindre|
|SPPLx	|Sphère / Plan|
|CDCDx	|ylindre / Cylindre|
|CDPLx	|Cylindre / Plan|
|PRPRx	|Polyèdre / Polyèdre|

**Corps déformables — Routines FEM**

–	mecaFEMx — Mécanique des solides : assemblage, calcul des forces internes (Fint), forces externes (Fext), matrice de rigidité (K) et résolution (ComputeDof).

–	therFEMx — Thermique : flux thermique, bilan d'énergie thermique, résolution ComputeDof.

–	hydrFEMx — Hydraulique : pression hydraulique, flux fluide, résolution ComputeDof.

**Contacteurs mixtes — Rigide / Déformable**

–	DKMECAx — Interaction entre disques rigides (2D) et maillages mécaniques (MECAx FEM 2D).

–	ALpMECAx — Interaction entre interfaces de maçonnerie (CLALp) et maillages mécaniques FEM 2D. Utile pour les simulations 
de structures maçonnées avec blocs déformables.

–	SPMECAx — Interaction entre sphères rigides (3D) et maillages mécaniques FEM 3D.

**Routines spéciales**

–	PT2Dx — Nœuds ponctuels 2D : interaction point/point pour les éléments câbles (ELASTIC_WIRE) et barres élastiques (ELASTIC_ROD).

–	PT3Dx — Équivalent 3D de PT2Dx.

–	NODES — Nœuds couplés : routines de couplage de degrés de liberté (COUPLED_DOF, NORMAL_COUPLED_DOF).

–	UpdateBulkBehav — Lois de comportement volumique : génère chipy.UpdateBulkBehav() pour les modèles avec plasticité, endommagement ou variables d'histoire.

#### 3.Extraction
Cet onglet configure toutes les sorties du calcul : fichiers de visualisation, visibilité des avatars, extraction de vecteurs d'état, forces de contact, énergie et champs FEM.

**Messages chipy (logs)**

–	Désactiver les messages chipy (utilities_DisableLogMes) — Génère chipy.utilities_DisableLogMes() immédiatement après chipy.Initialize(). Supprime tous les messages de progression dans la console. Recommandé pour les calculs en production ou de longue durée.

**Visualisation (WriteDisplayFiles)**

Contrôle l'écriture des fichiers de visualisation vers le répertoire DISPLAY/. Chaque case correspond à une famille d'avatars :
–	RBDY2_WriteDisplayFiles — Corps rigides 2D (coché par défaut).
–	RBDY3_WriteDisplayFiles — Corps rigides 3D.
–	mecaFEMx_WriteDisplayFiles — Maillages déformables mécaniques.
–	therFEMx_WriteDisplayFiles — Maillages déformables thermiques.
–	hydrFEMx_WriteDisplayFiles — Maillages déformables hydrauliques.
–	Écrire les fichiers display dans la boucle — Si coché, les fichiers sont écrits à chaque pas (ou à la fréquence définie). Si décoché, un seul fichier est écrit à la fin du calcul.

**Visibilité des avatars (SetVisible / SetInvisible)**

Permet d'afficher ou de masquer des avatars individuellement ou par groupe à des moments précis de la simulation. Chaque ligne de la liste correspond à une règle de visibilité.
Pour créer une règle, cliquer sur « + Créer une visibilité ». Chaque ligne contient :

|Action	|SetVisible ou SetInvisible — rend l'avatar visible ou invisible dans chipy.|
|---|-----|
|Dim.	|2D (RBDY2) ou 3D (RBDY3) — détermine le préfixe de la fonction générée.|
|IDs avatars	|Liste d'identifiants séparés par des virgules (ex. : 1, 3, 5). Prioritaire sur le groupe si les deux sont renseignés.|
|Groupe	|Nom d'un groupe d'avatars défini dans le projet. Résolu en liste d'IDs à la génération.|
|Mode / Timing	|Détermine quand l'appel est généré (voir tableau des modes ci-dessous).|

**Modes de temporisation (Timing)**

Modes de temporisation (Timing)

|Mode	|Condition générée	|Usage typique|
|---|---|---|
|Tous les pas	|Aucune condition (appel direct)	|Extraction systématique, bilan énergétique continu|
Tous les N pas	|if k % N == 0:	|Réduire la fréquence d'écriture pour alléger les sorties|
|Au pas k =	|if k == K:	|Événement ponctuel : changer la visibilité à un pas précis|
|Après boucle	|Hors de la boucle (après for k ...)	|État final uniquement, post-traitement en fin de calcul|

**Extraction de vecteurs d'état RBDY2 (RBDY2_GetBodyVector)**

Génère des appels à `chipy.RBDY2_GetBodyVector(vecteur, id)` dans la boucle de calcul. Pour chaque ligne ajoutée via « + Ajouter une extraction RBDY2 », configurer :

|Vecteur	|Nom du vecteur d'état à extraire (voir liste complète ci-dessous).|
|---|------|
|IDs avatars	|Liste d'IDs séparés par des virgules. Si renseigné, génère une boucle for sur ces IDs.|
|Groupe	|Groupe d'avatars à parcourir. Priorité inférieure aux IDs si les deux sont renseignés.|
|Mode / Timing	|Un des quatre modes de temporisation décrits ci-dessus.|

Vecteurs disponibles :
|Nom	|Description|
|---|----|
|Coor0	|Position de référence (configuration initiale)|
|Coor_	|Position courante|
|Coorb	|Position au pas précédent|
|Coorm	|Position moyenne entre deux pas|
|X____	|Déplacement total accumulé|
|V____	|Vitesse courante (linéaire et angulaire)|
|Vbeg_	|Vitesse en début de pas|
|Vfree	|Vitesse libre (avant résolution du contact)|
|Fext_	|Forces et moments extérieurs appliqués|
|Fint_	|Forces et moments internes|
|Reac_	|Résultante des réactions de contact|
|Ireac	|Impulsions de réaction de contact|

**Forces et réactions de contact**

–	Forces nodales (inter_handler_Rnod) — Extrait les forces nodales aux points de contact et les écrit dans POSTPRO/.
–	Vitesses locales (inter_handler_Vloc) — Extrait les vitesses relatives dans le repère local de contact.
–	Forces locales (inter_handler_Rloc) — Extrait les impulsions/forces dans le repère local de contact.

**Énergie**

–	Bilan énergétique global (ComputeEnergy + WriteEnergy) — Calcule et écrit l'énergie cinétique, potentielle et dissipée par frottement.
–	Énergie cinétique RBDY2 (RBDY2_KineticEnergy) — Écrit l'énergie cinétique de chaque corps rigide 2D séparément.

**Champs FEM (contraintes, déformations, température…)**

–	Champs par élément (mecaFEMx_WriteBodies) — Écrit les champs par élément : contraintes et déformations (MECAx), température (THERx), pression (HYDRx).
–	Variables internes (mecaFEMx_WriteInternalVariables) — Écrit les variables internes aux points de Gauss : plasticité, endommagement, variables d'histoire.


