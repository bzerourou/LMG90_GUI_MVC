# Assistant de configuration de projet

L'**Assistant de configuration de projet** guide pas à pas la création d'un projet LMGC90 complet avec tous ses éléments essentiels : matériau, modèle, avatar de test, loi de contact et table de visibilité.

Il est particulièrement utile pour démarrer rapidement un nouveau projet sans avoir à configurer chaque onglet séparément.

> **⏱️ Temps estimé : 2 à 3 minutes**

---

## Lancer l'assistant

Trois façons d'ouvrir l'assistant :

| Méthode | Action |
|---------|--------|
| Menu | **Fichier → Assistant de projet…** ou **Assistants → Configuration de projet** |
| Barre d'outils | Bouton dédié (selon la configuration de la barre) |
| Raccourci clavier | `Ctrl+Shift+N` |

![Ouverture de l'assistant](captures/projet_assistant.JPG)

> **Annulation possible à tout moment** : cliquer sur **❌ Annuler** à n'importe quelle étape ferme l'assistant sans modifier le projet. L'état du projet (nom, dimension, chemin) est entièrement restauré.

---

## Vue d'ensemble des étapes

L'assistant est composé de **9 pages** parcourues séquentiellement. Les boutons **⬅️ Retour** et **Suivant ➡️** permettent de naviguer librement entre les pages.

| Étape | Page | Description | Obligatoire |
|-------|------|-------------|-------------|
| 0 | Introduction | Présentation de l'assistant | — |
| 1 | Informations du projet | Nom et description | ✅ Oui (nom requis) |
| 2 | Dimension | 2D ou 3D | ✅ Oui |
| 3 | Matériau | Créer ou réutiliser un matériau | ✅ Oui |
| 4 | Modèle | Créer ou réutiliser un modèle physique | ✅ Oui |
| 5 | Avatar | Créer un premier avatar de test | ⬜ Optionnel |
| 6 | Loi de contact | Définir le comportement de contact | ⬜ Optionnel |
| 7 | Table de visibilité | Définir qui interagit avec qui | ⬜ Optionnel (requiert étapes 5 et 6) |
| 8 | Récapitulatif | Vérification avant création | — |

---

## Page 0 — Introduction

Page d'accueil présentant les étapes à venir. Aucune saisie requise.

Cliquer sur **Suivant ➡️** pour commencer.

---

## Page 1 — Informations du projet

![Page nom du projet](captures/projet_assistant_nom.JPG)

| Champ | Description | Contraintes |
|-------|-------------|-------------|
| **Nom du projet** | Identifiant du projet. Utilisé comme nom de fichier lors de la sauvegarde. | **Requis** — 50 caractères maximum. Le bouton Suivant est désactivé tant que ce champ est vide. |
| **Description** | Texte libre décrivant l'objectif ou le contexte du projet. | Optionnel |

> **Nom requis :** le champ Nom est marqué d'un astérisque (`*`) dans l'assistant — il s'agit d'un champ obligatoire. Le bouton **Suivant ➡️** reste grisé tant qu'il est vide.

---

## Page 2 — Dimension du problème

![Page dimension](captures/projet_assistant_dimension.JPG)

Choisir entre deux options exclusives (boutons radio) :

| Choix | Code interne | Exemples d'usage |
|-------|-------------|------------------|
| **2D — Problème bidimensionnel** | `dimension = 2` | Compression biaxiale, essai œdométrique, écoulement granulaire 2D, tambour rotatif 2D |
| **3D — Problème tridimensionnel** | `dimension = 3` | Compression triaxiale, trémie 3D, tambour cylindrique, mélangeur 3D |

La valeur **2D** est sélectionnée par défaut.

> **Effet sur les étapes suivantes :** la dimension choisie ici conditionne automatiquement :
> - La liste d'éléments proposés à l'étape Modèle (`Rxx2D` ou `Rxx3D`)
> - Le type d'avatar proposé à l'étape Avatar (`rigidDisk` ou `rigidSphere`)
> - Le type de corps et de contacteur dans la table de visibilité (`RBDY2/DISKx` ou `RBDY3/SPHER`)

---

## Page 3 — Matériau

![Page matériau](captures/projet_assistant_materiau.JPG)

Cette page propose deux modes selon l'état du projet :

### Mode A — Utiliser un matériau existant _(si le projet contient déjà des matériaux)_

Une liste déroulante affiche tous les matériaux déjà définis dans l'onglet Matériau. Sélectionner l'un d'eux pour l'associer au projet sans en créer un nouveau.

### Mode B — Créer un nouveau matériau _(coché automatiquement si aucun matériau n'existe)_

Cocher **Créer un nouveau matériau à la place** pour afficher le formulaire de création :

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant du matériau. **5 caractères maximum.** | `rockx` |
| **Type** | Type de comportement mécanique. | `RIGID` |
| **Densité** | Masse volumique (kg/m³). | `2500 kg/m³` |

> **Conseil de l'assistant :** pour des simulations granulaires simples, utilisez le type `RIGID` avec une densité de 2 500 kg/m³ (sable/gravier typique). Les propriétés élastiques ne sont pas configurables dans l'assistant — utiliser l'onglet Matériau pour les types `ELAS`, `ELAS_PLAS`, etc.

---

## Page 4 — Modèle physique

![Page modèle](captures/projet_assistant_modele.JPG)

Même logique que la page Matériau : réutiliser un modèle existant ou en créer un nouveau.

### Mode A — Utiliser un modèle existant

Liste déroulante des modèles déjà définis dans l'onglet Modèle.

### Mode B — Créer un nouveau modèle

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant du modèle. **5 caractères maximum.** | `rigid` |
| **Physique** | Famille de physique. | `MECAx` (seule option dans l'assistant) |
| **Élément** | Type d'élément fini. Adapté automatiquement à la dimension. | `Rxx2D` (2D) ou `Rxx3D` (3D) |

> **Conseil de l'assistant :** pour des corps rigides (DEM), utilisez `Rxx2D` en 2D ou `Rxx3D` en 3D. Ces éléments n'ont aucune option numérique et sont les plus simples à configurer. Pour des modèles éléments finis déformables, créer le modèle directement dans l'onglet Modèle après la fin de l'assistant.

---

## Page 5 — Premier avatar _(optionnel)_

![Page avatar](captures/projet_assistant_avatar.JPG)

Cette page est **optionnelle**. Elle permet de créer un avatar de test positionné à l'origine (centre = `[0, 0]` en 2D ou `[0, 0, 0]` en 3D).

Cocher **Créer un avatar de test** pour afficher le formulaire :

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Type** | Type d'avatar. Adapté automatiquement à la dimension. | `rigidDisk` (2D) ou `rigidSphere` (3D) |
| **Rayon** | Rayon du disque ou de la sphère (m). | `0.1 m` |
| **Couleur** | Code couleur LMGC90 à 5 caractères. | `BLUEx` |

> **Dépendance :** l'avatar utilise automatiquement le matériau et le modèle définis aux étapes précédentes. Si aucun matériau ou modèle valide n'est disponible, l'avatar ne sera pas créé même si la case est cochée.

> **Position :** l'avatar est créé à l'origine du repère. Modifier sa position après création via l'onglet Avatar.

---

## Page 6 — Loi de contact _(optionnelle)_

![Page loi de contact](captures/projet_assistant_contact.JPG)

Définit le comportement mécanique lors des contacts entre avatars. Cocher **Créer une loi de contact** (coché par défaut) pour afficher le formulaire :

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant de la loi. Jusqu'à 20 caractères. | `iqsc0` |
| **Type de loi** | Type de comportement de contact. Voir tableau ci-dessous. | `IQS_CLB` |
| **Coefficient de friction** | Visible uniquement pour les lois avec frottement de Coulomb. | `0.3` |

### Types de lois disponibles

| Type | Nom complet | Friction | Description |
|------|-------------|----------|-------------|
| `IQS_CLB` | Contact Unilatéral Quasi-Statique + Coulomb | ✅ Oui | Loi standard rigide non-lissée. La plus courante pour les simulations DEM. |
| `IQS_CLB_G0` | IQS_CLB avec gap nul | ✅ Oui | Variante avec gap initial nul. |
| `COUPLED_DOF` | Degrés de liberté couplés | ❌ Non | Couplage cinématique entre corps. |
| `IQS_DS_CLB` | Contact Discret Rigide + Coulomb | ❌ Non | Loi discrète avec rigidités normales et tangentielles. |
| `IQS_MOHR_DS_CLB` | Mohr-Coulomb Discret | ❌ Non | Critère de Mohr-Coulomb pour les joints ou interfaces fragiles. |
| `IQS_MAC_CZM` | Zone Cohésive | ❌ Non | Loi de zone cohésive pour la fissuration. |
| `ELASTIC_WIRE` | Câble élastique | ❌ Non | Liaison unilatérale en traction (câble). |
| `BRITTLE_ELASTIC_WIRE` | Câble élastique fragile | ❌ Non | Câble avec rupture fragile au-delà d'un seuil. |
| `ELASTIC_ROD` | Barre élastique | ❌ Non | Liaison bilatérale en traction et compression (barre). |
| `ELASTIC_REPELL_CLB` | Répulsion élastique + Coulomb | ❌ Non | Contact répulsif avec frottement. |

**Valeurs de friction typiques :**

| Matériau | Coefficient de friction |
|----------|------------------------|
| Surfaces lisses | 0.1 |
| Sable fin | 0.3 |
| Gravier | 0.5 |
| Béton rugueux | 0.6–0.8 |

> La friction n'est configurable que pour les lois `IQS_CLB` et `IQS_CLB_G0`. Pour les autres types, le champ est masqué automatiquement.

---

## Page 7 — Table de visibilité _(optionnelle)_

![Page visibilité](captures/projet_assistant_visibilite.JPG)

La table de visibilité définit **quels contacteurs peuvent se détecter mutuellement** et avec quelle loi de contact. Cocher **Créer une table de visibilité** (coché par défaut) pour afficher le formulaire :

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Couleur candidat** | Couleur des contacteurs candidats (corps actif). | `BLUEx` (synchronisé avec la couleur de l'avatar si l'étape 5 est active) |
| **Couleur antagoniste** | Couleur des contacteurs antagonistes (corps passif). | `BLUEx` |
| **Distance d'alerte** | Distance maximale de détection de contact (m). Au-delà, deux corps ne sont pas considérés en contact potentiel. | `0.1 m` |

**Configuration automatique selon la dimension :**

| Paramètre | 2D | 3D |
|-----------|----|----|
| Type de corps | `RBDY2` | `RBDY3` |
| Type de contacteur | `DISKx` | `SPHER` |
| Loi de contact | Celle créée à l'étape 6 | Celle créée à l'étape 6 |

> **Dépendance :** la table de visibilité n'est créée que si une loi de contact a été définie à l'étape précédente **et** qu'un avatar a été créé à l'étape 5. Si l'une ou l'autre de ces conditions n'est pas remplie, la table est ignorée même si la case est cochée.

> **Synchronisation des couleurs :** si un avatar a été créé à l'étape 5, les couleurs candidat et antagoniste sont automatiquement pré-remplies avec la couleur de cet avatar.

---

## Page 8 — Récapitulatif

![Page récapitulatif](captures/projet_assistant_recap.JPG)

La dernière page affiche un résumé complet de tous les éléments qui seront créés. Vérifier les informations avant de valider.

### Contenu du récapitulatif

| Section | Informations affichées |
|---------|------------------------|
| **Projet** | Nom du projet, dimension (2D/3D) |
| **Matériau** | Nom, type, densité — ou matériau existant sélectionné |
| **Modèle** | Nom, physique, élément — ou modèle existant sélectionné |
| **Avatar** | Type, rayon — ou « Aucun avatar créé » |
| **Loi de contact** | Nom, type, coefficient de friction — ou « Aucune loi créée » |
| **Table de visibilité** | Corps, contacteur, couleurs, loi appliquée, distance d'alerte — ou « Aucune table créée » |

Cliquer sur **✅ Créer le Projet** pour finaliser. Tous les éléments sont créés simultanément et apparaissent immédiatement dans l'arbre du modèle et les onglets correspondants.

> **En cas d'erreur :** si la création échoue (nom de matériau en double, paramètre invalide, etc.), une boîte d'erreur s'affiche avec le détail du problème. L'état du projet est entièrement restauré à son état avant l'ouverture de l'assistant.

---

## Après la création

Une fois l'assistant terminé, tous les éléments générés sont modifiables librement via leurs onglets respectifs :

| Élément créé | Onglet pour modifier |
|-------------|---------------------|
| Matériau | **Matériau** (`Ctrl+1`) — sélectionner dans la liste et cliquer sur ✏️ Modifier |
| Modèle | **Modèle** (`Ctrl+2`) |
| Avatar | **Avatar** (`Ctrl+3`) |
| Loi de contact | **Contact** (`Ctrl+9`) |
| Table de visibilité | **Visibilité** |

---

## Récapitulatif des raccourcis

| Action | Raccourci |
|--------|-----------|
| Ouvrir l'assistant | `Ctrl+Shift+N` |
| Page suivante | `Entrée` ou **Suivant ➡️** |
| Page précédente | **⬅️ Retour** |
| Annuler | **❌ Annuler** (restaure l'état précédent) |
| Créer le projet | **✅ Créer le Projet** (dernière page) |

---

## Conseils d'utilisation

**Commencer simple :** pour un premier projet LMGC90_GUI 2D, utiliser le type `RIGID` pour le matériau, `Rxx2D` pour le modèle, créer un disque de test et la loi `IQS_CLB` avec un frottement de 0.3. Le projet sera fonctionnel en moins de 2 minutes.

**Réutiliser l'existant :** si un matériau ou un modèle a déjà été créé dans le projet courant, l'assistant le propose automatiquement en première option. Il n'est pas nécessaire d'en créer un nouveau à chaque fois.

**Compléter après :** l'assistant crée des éléments de base. Pour vos configurations avancées (éléments finis déformables, lois plastiques, conditions aux limites, boucles granulaires), utiliser directement les onglets spécialisés après la fin de l'assistant.