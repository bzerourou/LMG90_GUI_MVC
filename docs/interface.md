# Introduction à l'interface de LMGC90_GUI

LMGC90_GUI est une interface graphique moderne et intuitive conçue pour faciliter la création de vos modèles numériques avec le module **pre** (pré-processeur) de **LMGC90**.

Il est tout à fait possible de lancer vos calculs sur LMGC90_GUI (module **chipy**).

L'interface est organisée de manière claire et ergonomique pour accompagner l'utilisateur du début à la fin du processus de modélisation : création des éléments, conditions aux limites, post-traitement,  génération des fichiers et enfin calculs.

Voici cette vidéo qui explique la vue d'ensemble des différentes parties de l'interface.

[![Introduction LMGC90_GUI](https://img.youtube.com/vi/2lVIGg3VboA/0.jpg)](https://www.youtube.com/watch?v=2lVIGg3VboA)


## Fenêtre principale

![Vue globale de l'interface](captures/interface_sections.jpg)

L'interface est divisée en **quatre zones principales** :

1. **Menu**
2. **Barre d'outils** (en haut)
3. **Arbre du modèle** (à gauche)
4. **Onglets de création** (centre haut)
5. **Zone de rendu** (centre bas)
6. **Barre d'état** (en bas)

### 1. Menu et Barre d'outils

#### Menu
- **Fichier** :
  - Nouveau  (Ctrl+N) : 
  Sert  à créer un nouveau projet, vous cliquez sur le bouton "nouveau" de la barre d'outils, ou de cliquer sur le menu "Fichier" -> "Nouveau", ou avec le raccourci clavier "Ctrl+N", une petit boite de dialogue s'ouvre pour renseigner le nom de votre projet

  ![](captures/nouveau_projet.JPG)

  - Ouvrir (Ctrl+O)
  Sert à ouvrir vos projets existants pour pouvoir leurs apportés des modifications,  cliquez simplement sur le bouton "Ouvrir" de la barre d'outils, ou cliquez sur le menu "Fichier"->"Ouvrir", sinon avec me raccouri clavier "Ctrl+O", ensuite il vous restera seulement de spécifier le chemin et nom de votre projet

  ![](captures/ouvrir_projet.JPG)

  - Sauvegarder (Ctrl+S)
  Sert à sauvegarder vos projets dans votre disque dur, cliquez sur le bouton "sauvegarder" de la barre d'outils, ou de cliquez sur le menu "Fichier"-> "Sauvegarder", ou avec le raccourci clavier "Ctrl+S",
  - Sauvegarder sous... (Ctrl+Shift+S)
  - Quiter (Ctrl+Q)

- **Assistants**

  - Assistant de configuration de projets (Ctrl+Shift+N)
  Est un assistant qui vous guidera pas à pas pour créer et configurer votre projet

  ![](captures/assistant_projet.JPG)

  - Assistant de granulométrie (Ctrl+Shift+G)
  Est un assistant pour générer une granulométrie rapidement avec les routines liées à pylmgc90, idéal pour les dépôt qui ne dépasse pas 8000 avatars, sinon l'application prend beaucoup plus de temps afin de rafraichir l'UI, parfois plante complètement.

  ![](captures/assistant_granulo_pylmgc90.JPG)

  - Génération granulométrie numpy... (bêta)
  Est une boite de dialogue qui sert à générer et dépose des avatars à base de numpy sans passer par les routines pylmgc90, idéal pour la génération plus de 5000 avatars 

  ![](captures/assistant_granulo_numpy.JPG) 
  
  - Assistant de déformable.. (Ctrl+Shift+D)
  Est un assistant qui vous guidera dans la création ou importation de vos éléments déformables

  ![](captures/assistant_defor_page1.JPG)

  - Assistant de maçonnerie (Ctrl+Shift+M)
  Est un assistant spécialisé dans la maçonnerie, il va vous permettre de créer vos empilement de brick2D/brick3D sous différentes façons  

  ![](captures/assistant_maçon_page1.JPG)

**Important**  : Vous pourrez utiliser les assistants autant de fois que vous vouliez  

- **Outils** :

  - Générer DATBOX 
  - Générer Script Python  
  - Variables dynamiques (Ctrl+V) 
    Cette boite de dialogue vous permet de créer des variables que vous pourriez utiliser afin d'automatiser saisies, il est aussi une fenêtre vers les propriétés de vos objets LMGC90, 
    ![](captures/variables.JPG)

  - Préférences (Ctrl+,) : [Préférences](#5-préférences)
- **Calcul**
  - Paramètres de calcul (Ctrl+F5)
  - Lancer calcul (F5)
  - Générer Script Calcul 
  - Voir logs LMGC90 (F6)
  - Journal de l'application (F7)  :

  Cette boîte de dialogue sera en quelque sorte une brèche de LMGC90_GUI vers le code LMGC90 afin de voir certaines erreurs non gérées par l'application
  
  ![](captures/journal_app.JPG)

- **Onglets**
  - Ouvrir : [Onglets de création](#3-onglets-de-création-zone-centrale-supérieure)
  - Fermer les autres 
  - Fermer tous (sauf essentiels) 
  - Onglets par défauts (Ctrl+Alt+D)
- **Help** :
  - À propos 
  - Aide en ligne

  ### Barre d'outils
I'interface comporte une barre d'outils pour  les actions les plus fréquentes :
- Nouveau projet
- Ouvrir projet
- Sauvegarder projet
- Générer script Python
- Générer Datbox (depuis v0.2.6)

### 2. Arbre du modèle (à gauche)

Zone fixe en forme d'arbre contenant l’**arborescence complète du modèle en cours**.

#### Sections affichées :
- **Matériaux** 
- **Modèles** 
- **Avatars** 
- **Groupes d'avatars** (boucles, granulométrie)
- **Lois de contact**
- **Tables de visibilité**
- **PostPro**

Fonctionnalités :
- Cliquez sur un élément → pointe sur l’onglet correspondant dans le cas ouvert en _mode édition_
- Vue hiérarchique claire de tous  les éléments du projet



### 3. Onglets de création (zone centrale supérieure)

Zone principale de travail avec des onglets dédiés à chaque étape de modélisation, il vous suffit simplement de cliquer sur le menu "**Onglets**" puis "Ouvrir" et de choisir l'onglet voulu :

![](captures/onglets.jpg)

- **Matériau** : création et gestion des matériaux
- **Modèle** : définition des modèles physiques et éléments
- **Avatar** : création de corps rigides simples (disque, polygone, mur, etc.)
- **Avatar vide** : création d'avatars vides avec contacteurs multiples
- **Bibliothèques** : contients des avatars déjà personnalisés, 
- **Boucles** : génération paramétrique (cercle, grille, ligne, spirale, manuel)
- **Granulométrie** : génération de dépôts avec distribution
- **DOF** : conditions aux limites (translation, rotation, vitesses imposées)
- **Contact** : lois de contacts
- **Visibilité** : tables de détection
- **Postpro** : commandes de sortie (énergie, suivi de corps, etc.)
- **Visualisation** : Ouvre un onglet pour visualisation des avatars de vos modèles

Des raccourcis clavier sont disponibles pour les neuf premiers onglets.(Ctrl+ 1,2,3, etc)



### 4. Zone de rendu (zone centrale inférieure)

Partie dédiée à la visualisation et aux sorties.

#### Boutons disponibles :
- **LMGC90 visualisation** : lance la visualisation intégrée avec `pre.visuAvatars()`
- **ParaView** : ouvre automatiquement les fichiers de sortie dans ParaView (par défaut rigids.pvd)

**Paraview** s'ouvre seulement s'il est installé dans votre machine, et seulement si vous avez déjà un résultat d'un calcul (simulation).


### 5. Préférences
Vous pouvez personnalisé LMGC90_GUI à travers le menu "Outils " -> "Préférences", ou bien avec le raccouri clavier "ctrl+,", une boite de dialogue s'ouvrira sur votre écran, 
Vous avez la possibilité de spécifier quatre choses : 
- Un chemin pour vos projets en cliquant sur le bouton "Parcourir"
- Choisir un système d'unités (SI ou CSG), il n'est pas encore implémenter
- Automatiser vos sauvegardes en cochant les options 
- Préciser nombre de projets de votre historique
- Activer/désactiver l'affichage des avatars dans l'arbre de création et dans le tableau qui liste les avatars dans l'onglet avatars.

![](captures/preferences.JPG)


### 6. Barre d'état 

Affiche des messages d'informations sur l'état des opérations en cours.

---

LMGC90_GUI est conçue pour être **intuitive**,  et **entièrement visuelle**, tout en conservant la pleine compatibilité avec les scripts Python traditionnels de LMGC90.
