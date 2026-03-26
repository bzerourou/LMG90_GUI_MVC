# Création d'un Matériau

L'onglet **Matériau**  explique comment créer/modifier/supprimer et configurer un matériau dans LMGC90_GUI.


[![Introduction LMGC90_GUI](https://img.youtube.com/vi/6OiwBiSzL_E/0.jpg)](https://www.youtube.com/watch?v=6OiwBiSzL_E)


## Interface
L'inglet **Matériau** est divisé en deux parties : 
- **Liste des matériaux** (en haut) : tableau affichant tous les matériaux définis dans le projet avec leur nom, type, densité et un aperçu des propriétés. Les matériaux utilisés par au moins un avatar sont affichés en vert.
- **Formulaire de création / modification** (en bas) : champs de saisie adaptés au type sélectionné.



### Champs du formulaire
 
| Champ | Description |
|-------|-------------|
| **Nom** | Identifiant unique du matériau. **5 caractères maximum** (contrainte interne LMGC90). Exemples : `TDURx`, `ROCKx`, `steel`, `BEton`. |
| **Type** | Liste déroulante des types de matériaux supportés. Détermine les propriétés attendues dans le champ suivant. |
| **Densité** | Masse volumique en kg/m³ (système SI). Valeur par défaut : `2800`. |
| **Propriétés** | Champ texte libre pour les paramètres spécifiques au type, au format `cle=valeur, cle=valeur`. Rempli automatiquement avec une suggestion cohérente à chaque changement de type. |
 
> **Suggestion automatique :** à chaque sélection d'un nouveau type, le champ Propriétés et le nom sont remplis automatiquement avec des valeurs typiques. Ces valeurs servent de point de départ et doivent être adaptées au matériau réel.

---
 
## Types de matériaux disponibles
 
LMGC90_GUI propose **10 types** de matériaux, correspondant aux types acceptés par `pre.material(materialType=…)` dans pylmgc90.
 
> **Note :** les types marqués _(avancé)_ — `DISCRETE`, `USER_MAT`, `EXTERNAL` — ne disposent pas de suggestion automatique dans l'interface. Leurs paramètres doivent être renseignés manuellement.
 
### Tableau des paramètres
 
| Type | Nom complet | Paramètres principaux | Physique compatible |
|------|-------------|-----------------------|---------------------|
| `RIGID` | Corps rigide | _(aucun)_ | MECAx |
| `ELAS` | Élastique linéaire | `elas`, `young`, `nu`, `anisotropy` | MECAx |
| `ELAS_DILA` | Élastique avec dilatation thermique | `elas`, `young`, `nu`, `anisotropy`, `dilatation`, `T_ref_meca` | MECAx, THERx |
| `VISCO_ELAS` | Visco-élastique | `elas`, `young`, `nu`, `anisotropy`, `viscous_model`, `viscous_young`, `viscous_nu` | MECAx |
| `ELAS_PLAS` | Élasto-plastique | `elas`, `young`, `nu`, `anisotropy`, `critere`, `isoh`, `iso_hard`, `isoh_coeff`, `cinh`, `visc` | MECAx |
| `THERMO_ELAS` | Thermo-élastique couplé | `elas`, `young`, `nu`, `anisotropy`, `dilatation`, `T_ref_meca`, `conductivity`, `specific_capacity` | THERx, THMx |
| `PORO_ELAS` | Poro-élastique (Biot) | `elas`, `young`, `nu`, `anisotropy`, `hydro_cpl`, `conductivity`, `specific_capacity` | POROx, THMx |
| `DISCRETE` _(avancé)_ | Éléments discrets (masse-ressort) | `masses`, `stiffnesses`, `viscosities` | MECAx |
| `USER_MAT` _(avancé)_ | Loi de comportement personnalisée | `density`, `file_mat` | MECAx |
| `EXTERNAL` _(avancé)_ | Interface avec code externe | _(définis par le code externe)_ | MECAx |
 
### Tableau des usages typiques
 
| Type | Applications typiques | Exemples concrets | Domaines |
|------|-----------------------|-------------------|----------|
| `RIGID` | Méthode des éléments discrets (DEM) | Empilements de grains, écoulements granulaires, assemblages de particules | Génie civil, pharmacie, agroalimentaire |
| `ELAS` | Structures en régime élastique | Bâtiments, ponts, pièces mécaniques, structures métalliques | Génie civil, mécanique |
| `ELAS_DILA` | Contraintes thermiques unilatérales | Structures soumises à des variations de température, dilatation différentielle | Bâtiment, mécanique, électronique |
| `VISCO_ELAS` | Matériaux à comportement visqueux | Polymères, asphalte, matériaux amortissants, joints d'étanchéité | Routes, automobile, aéronautique |
| `ELAS_PLAS` | Déformations plastiques permanentes | Formage des métaux, impact, endommagement, usinage | Métallurgie, automobile, aéronautique |
| `THERMO_ELAS` | Couplage thermo-mécanique complet | Dissipation thermique, chocs thermiques, freinage | Électronique, automobile, nucléaire |
| `PORO_ELAS` | Milieux poreux saturés | Consolidation de sols, réservoirs pétroliers, aquifères, stockage CO₂ | Géotechnique, hydrogéologie, pétrole |
| `DISCRETE` | Systèmes masse-ressort-amortisseur | Isolateurs sismiques, suspensions, liaisons élastiques discrètes | Génie parasismique, automobile |
| `USER_MAT` | Lois de comportement sur mesure | Matériaux spécifiques, lois issues de l'expérience | Recherche, matériaux innovants |
| `EXTERNAL` | Couplage avec un code externe | Interface avec d'autres logiciels de simulation | Simulation multi-physique |
 
---
## Propriétés détaillées par type
 
### RIGID — Corps rigide
 
Aucun paramètre de propriété n'est requis. Le champ Propriétés doit rester vide.
 
```
Nom      : BRIQx
Type     : RIGID
Densité  : 2000
Propriétés : (vide)
```
 
---
 
### ELAS — Élastique linéaire
 
```
elas='standard', young=2.1e11, nu=0.3, anisotropy='isotropic'
```
 
| Paramètre | Description | Valeur typique |
|-----------|-------------|----------------|
| `elas` | Formulation élastique : toujours `'standard'`. | `'standard'` |
| `young` | Module de Young (Pa). | Acier : `2.1e11` · Béton : `3e10` · Roche : `5e10` |
| `nu` | Coefficient de Poisson (sans dimension). | `0.2` à `0.35` |
| `anisotropy` | Type d'anisotropie : `'isotropic'` ou `'orthotropic'`. | `'isotropic'` |
| `G`|  Module de cisaillement (Pa) |  Acier : `8.1e10`|     
 
---
 
### ELAS_DILA — Élastique avec dilatation thermique
 
```
elas='standard', young=3e10, nu=0.2, anisotropy='isotropic', dilatation=1.2e-5, T_ref_meca=20.0
```
 
| Paramètre | Description | Valeur typique |
|-----------|-------------|----------------|
| `elas` | Formulation élastique. | `'standard'` |
| `young` | Module de Young (Pa). | `3e10` |
| `nu` | Coefficient de Poisson. | `0.2` |
| `anisotropy` | Anisotropie. | `'isotropic'` |
| `dilatation` | Coefficient de dilatation thermique linéique (K⁻¹). | `1e-5` à `2e-5` |
| `T_ref_meca` | Température de référence mécanique (°C ou K) — déformation thermique nulle à cette valeur. | `20.0` |
 
---
 
### VISCO_ELAS — Visco-élastique
 
```
elas='standard', anisotropy='isotropic', young=1.17e11, nu=0.35,
viscous_model='KelvinVoigt', viscous_young=1.17e9, viscous_nu=0.35
```
 
| Paramètre | Description | Valeurs |
|-----------|-------------|---------|
| `elas` | Formulation élastique. | `'standard'` |
| `young` | Module de Young de la branche élastique (Pa). | `1.17e11` |
| `nu` | Coefficient de Poisson élastique. | `0.35` |
| `anisotropy` | Anisotropie. | `'isotropic'` |
| `viscous_model` | Modèle rhéologique. `KelvinVoigt` = ressort et amortisseur en parallèle (fluage réversible).  | `'KelvinVoigt'` · `'none'` |
| `viscous_young` | Module de Young de la branche visqueuse (Pa). | `1.17e9` |
| `viscous_nu` | Coefficient de Poisson de la branche visqueuse. | `0.35` |
 
---
 
### ELAS_PLAS — Élasto-plastique
 
```
elas='standard', anisotropy='isotropic', young=2.1e11, nu=0.3,
critere='Von-Mises', isoh='linear', iso_hard=2.5e8, isoh_coeff=1e9,
cinh='none', visc='none'
```
 
| Paramètre | Description | Valeurs |
|-----------|-------------|---------|
| `elas` | Formulation élastique. | `'standard'` |
| `young` | Module de Young (Pa). | `2.1e11` |
| `nu` | Coefficient de Poisson. | `0.3` |
| `anisotropy` | Anisotropie. | `'isotropic'` . `'orthotropic'`  |
| `critere` | Critère de plasticité. | `'Von-Mises'` · `'none'` |
| `isoh` | Type d'écrouissage isotrope. | `'none'`, `'linear'`   |
| `iso_hard` | Limite d'élasticité initiale σ₀ (Pa). | `2.5e8` |
| `isoh_coeff` | Module d'écrouissage isotrope H (Pa). | `1e9` |
| `cinh` | Écrouissage cinématique. | `'none'` |
| `visc` | Viscoplasticité. | `'none'` |
 
---
 
### THERMO_ELAS — Thermo-élastique couplé
 
```
elas='standard', young=3e10, nu=0.2, anisotropy='isotropic',
dilatation=1.2e-5, T_ref_meca=20.0, conductivity=1.8, specific_capacity=880.0
```
 
| Paramètre | Description | Valeur typique |
|-----------|-------------|----------------|
| `elas` | Formulation élastique. | `'standard'` |
| `young` | Module de Young (Pa). | `3e10` |
| `nu` | Coefficient de Poisson. | `0.2` |
| `anisotropy` | Anisotropie. | `'isotropic'` |
| `dilatation` | Coefficient de dilatation thermique (K⁻¹). | `1.2e-5` |
| `T_ref_meca` | Température de référence mécanique. | `20.0` |
| `conductivity` | Conductivité thermique (W/m/K) ou `'field'` |
| `specific_capacity` | Capacité thermique massique (J/kg/K) ou `'field'`|
 
---
 
### PORO_ELAS — Poro-élastique (Biot)
 
```
elas='standard', young=5e7, nu=0.3, anisotropy='isotropic',
hydro_cpl=0.8, conductivity=1e-8, specific_capacity=1e-10
```
 
| Paramètre | Description | Valeur typique |
|-----------|-------------|----------------|
| `elas` | Formulation élastique. | `'standard'` |
| `young` | Module de Young du squelette solide (Pa). | `5e7` |
| `nu` | Coefficient de Poisson du squelette. | `0.3` |
| `anisotropy` | Anisotropie. | `'isotropic'` |
| `hydro_cpl` | Coefficient de couplage de Biot (0 à 1). | `0.8` |
| `conductivity` | Conductivité hydraulique (m/s) ou `'field'` |
| `specific_capacity` | Capacité de stockage hydraulique (Pa⁻¹) ou `'field'`|
 
---
 
## Exemple de création — acier élastique
 
1. Ouvrir l'onglet **Matériau** (`Ctrl+1`).
2. Sélectionner le type **ELAS** dans la liste déroulante — le champ Propriétés se remplit automatiquement.
3. Modifier les valeurs dans le champ Propriétés :
 
```
elas='standard', young=2.1e11, nu=0.3, anisotropy='isotropic'
```
 
4. Régler la densité à `7850` kg/m³.
5. Saisir un nom : `steel` ou `ACIEx`.
6. Cliquer sur **✅ Créer Matériau**.
 
![Création d'un matériau acier](captures/materiau_steel.JPG)
 
---
 
## Modification et suppression
 
Dans le tableau de la liste des matériaux, sélectionnez le matériau à modifier puis cliquez sur le bouton **✏️ Modifier Sélection**. Toutes les données du matériau sont chargées dans le formulaire en mode **Édition**.
 
- Apportez vos modifications dans les champs.
- Cliquez sur **💾 Enregistrer Modifications** pour valider.
- Cliquez sur **❌ Annuler** pour ignorer les changements et revenir au mode normal.
 
![Modification d'un matériau](captures/materiau_steel_modification.JPG)
 
> **Suppression :** un matériau utilisé par au moins un avatar ne peut pas être supprimé directement. Un message d'avertissement indique les avatars concernés. Il faut d'abord réassigner ces avatars à un autre matériau, ou les supprimer.
 
---
 
## Variables dynamiques
 
Les variables dynamiques permettent de définir des valeurs ou expressions réutilisables dans tous les champs numériques de l'interface, y compris dans le champ Propriétés des matériaux.
 
Ouvrez la boîte de dialogue via **Outils → Variables dynamiques** ou le raccourci `Ctrl+V`.
 
![Variables dynamiques](captures/variables.JPG)
 
### Comment créer une variable
 
1. Dans la boîte de dialogue, cliquez sur l'un des exemples pour le charger comme base (optionnel).
2. Saisissez le **nom** de la variable (ex : `young_ref`).
3. Saisissez la **valeur ou expression** (ex : `2.1e11`).
4. Cliquez sur **Ajouter ou modifier**.
5. Cliquez sur **OK** pour fermer.
 
Les variable dynamiques sont désormais utilisable dans n'importe quel champ de l'application en tapant son nom directement. Voir [Variables dynamiques](dynam_variables.md).
 
### Exemples d'expressions
 
| Expression saisie | Résultat | Usage |
|-------------------|----------|-------|
| `young_ref = 2.1e11` | Constante numérique | `young=young_ref` dans les propriétés |
| `young_beton = young_ref / 7` | Expression calculée | Rapport de rigidité béton/acier |
| `nu_courant = 0.3` | Constante | Coefficient de Poisson par défaut |
| `radius = avatar[0].radius * 2` | Propriété d'un avatar existant | Rayon dérivé d'un autre avatar |
 
> **Remarque :** les expressions sont évaluées via `SafeEvaluator`, qui autorise les opérations mathématiques Python standard (`+`, `-`, `*`, `/`, `**`, `math.sqrt(…)`, etc.) ainsi que l'accès aux propriétés des avatars et matériaux du projet.
 
---
 
## Astuces
 
- **Nom limité à 5 caractères** : Les noms en LMGC90 sont sur cinq caractères. Préférez des codes courts comme `steel`, `BEton`, `GRAN1`.
- **Matériau RIGID sans propriétés** : pour les corps rigides, le champ Propriétés doit rester vide. Seule la densité est utilisée pour le calcul de la masse et du moment d'inertie.
- **Valeur `'field'`** : pour `conductivity` et `specific_capacity` des types `THERMO_ELAS` et `PORO_ELAS`, la valeur `'field'` indique que ce paramètre est défini par le modèle éléments finis et non par une constante scalaire.
- **Cohérence matériau / modèle** : le type du matériau doit être compatible avec la physique du modèle associé à l'avatar. Par exemple, un matériau `PORO_ELAS` doit être associé à un modèle de physique `POROx` ou `MULTI`.
- **Variables dynamiques** : utilisez `Ctrl+V` pour accéder rapidement aux variables et éviter les saisies répétitives dans les champs Propriétés.