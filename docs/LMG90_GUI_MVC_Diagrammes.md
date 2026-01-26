
# LMG90_GUI_MVC — Schéma complet (Architecture, Classes, Séquences)

> **Version :** 2026-01-24 19:12  > **Auteur :** M365 Copilot  > **Portée :** Schémas basés sur la structure publique du dépôt *LMG90_GUI_MVC* et le périmètre fonctionnel de *LMGC90*. Les éléments marqués **[présumé]** sont déduits du contexte et à confirmer par lecture des sources.

---

## Sommaire
- [1) Vue d’ensemble — Architecture (MVC)](#1-vue-densemble--architecture-mvc)
- [2) Diagrammes de classes](#2-diagrammes-de-classes)
  - [2.1. Modèle (core)](#21-modèle-core)
  - [2.2. Validation / Génération / Sérialisation / Bridge](#22-validation--génération--sérialisation--bridge)
  - [2.3. Contrôleur](#23-contrôleur)
  - [2.4. Vues (PyQt6)](#24-vues-pyqt6)
  - [2.5. Utilitaires (sécurité)](#25-utilitaires-sécurité)
- [3) Diagrammes de séquence (workflows clés)](#3-diagrammes-de-séquence-workflows-clés)
  - [3.1. Ajouter un matériau](#31-ajouter-un-matériau)
  - [3.2. Générer une boucle d’avatars](#32-générer-une-boucle-davatars)
- [4) Hypothèses & limites](#4-hypothèses--limites)
- [5) Références](#5-références)

---

## 1) Vue d’ensemble — Architecture (MVC)

```mermaid
flowchart LR
  subgraph View[View (PyQt6)]
    MW[MainWindow]
    TV[TreeView]
    DLG[Dialogs]
    TABS[Tabs
(MaterialTab, AvatarTab, ...)]
  end

  subgraph Controller[Controller]
    PC[ProjectController]
  end

  subgraph Model[Model (core)]
    MOD[models.py
(Material, MaterialType, Loop, [Project]…)]
    VAL[validators.py
(MaterialValidator, LoopValidator, …)]
    GEN[generators.py
(LoopGenerator, [GranuloGenerator]…)]
    SER[serializers.py
(JsonSerializer [présumé])]
    BR[pylmgc_bridge.py
(PylmgcBridge)]
  end

  subgraph Utils[Utils]
    SE[SafeEvaluator (AST)]
  end

  MW -->|signals/slots| PC
  TABS -->|signals/slots| PC
  TV -->|refresh via adapter| PC
  DLG -->|inputs| PC

  PC --> MOD
  PC --> VAL
  PC --> GEN
  PC --> SER
  PC --> BR
  VAL --> SE
  PC --> SE
```

---

## 2) Diagrammes de classes

### 2.1. Modèle (core)

> Champs affichés quand explicitement visibles dans la documentation/exemples. D’autres entités sont **[présumées]** d’après le périmètre LMGC90/GUI.

```mermaid
classDiagram
  direction LR

  class MaterialType {
    <<Enum>>
    +RIGID
    +ELAS
    +ELAS_DILA
    +VISCO_ELAS
    +ELAS_PLAS
    +THERMO_ELAS
    +PORO_ELAS
  }

  class Material {
    <<dataclass>>
    +name: str
    +material_type: MaterialType
    +density: float
    +properties: dict
  }

  class Loop {
    <<dataclass>>
    +loop_type: str
    +model_avatar_index: int
    +count: int
    +radius: float
    +group_name: str
  }

  class Project {
    <<[présumé]>>
    +materials: list~Material~
    +avatars: list~Avatar~
    +contact_laws: list~ContactLaw~
    +boundary_conditions: list~BoundaryCondition~
    +variables: dict
  }

  class Avatar {
    <<[présumé]>>
    +id: int
    +shape: str
    +params: dict
    +group: str
  }

  class ContactLaw {
    <<[présumé]>>
    +name: str
    +type: str
    +params: dict
  }

  class BoundaryCondition {
    <<[présumé]>>
    +name: str
    +target: str
    +type: str
    +params: dict
  }

  Project "1" o-- "*" Material
  Project "1" o-- "*" Avatar
  Project "1" o-- "*" ContactLaw
  Project "1" o-- "*" BoundaryCondition
  Material --> MaterialType
```

### 2.2. Validation / Génération / Sérialisation / Bridge

```mermaid
classDiagram
  direction LR

  class BaseValidator {
    <<[présumé]>>
    +validate(obj) None|Error
  }

  class MaterialValidator {
    +validate(material: Material)
  }

  class LoopValidator {
    +validate(loop: Loop)
  }

  BaseValidator <|-- MaterialValidator
  BaseValidator <|-- LoopValidator

  class BaseGenerator {
    <<[présumé]>>
    +run(project: Project, params: dict) list~int~
  }

  class LoopGenerator {
    +run(project: Project, loop: Loop) list~int~
  }

  BaseGenerator <|-- LoopGenerator

  class JsonSerializer {
    <<[présumé]>>
    +save(project: Project, path: str)
    +load(path: str) Project
  }

  class PylmgcBridge {
    +to_datbox(project: Project, path: str)
    +to_chipy(project: Project) [présumé]
  }
```

### 2.3. Contrôleur

```mermaid
classDiagram
  direction TB

  class ProjectController {
    +add_material(m: Material) None
    +generate_loop(loop: Loop) list~int~
    +save_project(path: str) None
    +load_project(path: str) Project
    +export_datbox(path: str) None
    +get_view_models() dict [présumé]
  }

  ProjectController --> Material
  ProjectController --> Loop
  ProjectController --> Project
  ProjectController --> PylmgcBridge
  ProjectController --> JsonSerializer
  ProjectController --> MaterialValidator
  ProjectController --> LoopValidator
```

### 2.4. Vues (PyQt6)

```mermaid
classDiagram
  direction TB

  class MainWindow {
    <<QMainWindow>>
    +setupUi()
    +connectSignals()
    +bindController(ProjectController)
  }

  class TreeView {
    <<QWidget/QTreeView>>
    +setModel(data)
    +refresh()
  }

  class Dialogs {
    <<QDialog>>
    +getUserInput() dict
  }

  class MaterialTab {
    <<QWidget>>
    +readForm() Material
    +populate(materials: list~Material~)
  }

  class AvatarTab {
    <<QWidget>>
    +configureLoop() Loop
    +populate(avatars: list~Avatar~)
  }

  MainWindow o-- MaterialTab
  MainWindow o-- AvatarTab
  MainWindow o-- TreeView
  MainWindow o-- Dialogs
  MainWindow --> ProjectController
```

### 2.5. Utilitaires (sécurité)

```mermaid
classDiagram
  direction LR

  class SafeEvaluator {
    +eval_expression(expr: str) Any
    +eval_dict(exprs: str) dict
  }

  SafeEvaluator <.. MaterialValidator
  SafeEvaluator <.. ProjectController
```

---

## 3) Diagrammes de séquence (workflows clés)

### 3.1. Ajouter un matériau

```mermaid
sequenceDiagram
  autonumber
  participant User as Utilisateur
  participant View as MaterialTab
  participant Ctrl as ProjectController
  participant Val as MaterialValidator
  participant Model as Project

  User->>View: Remplit le formulaire (name, type, density, properties)
  View->>Ctrl: add_material(material)
  Ctrl->>Val: validate(material)
  Val-->>Ctrl: OK (ou ValidationError)
  alt OK
    Ctrl->>Model: Project.materials.append(material)
    Ctrl-->>View: succès + rafraîchissement
  else Erreur
    Ctrl-->>View: message d'erreur
  end
```

### 3.2. Générer une boucle d’avatars

```mermaid
sequenceDiagram
  autonumber
  participant User as Utilisateur
  participant View as AvatarTab
  participant Ctrl as ProjectController
  participant Val as LoopValidator
  participant Gen as LoopGenerator
  participant Model as Project

  User->>View: Paramètre la boucle (type, count, radius, group)
  View->>Ctrl: generate_loop(loop)
  Ctrl->>Val: validate(loop)
  Val-->>Ctrl: OK
  Ctrl->>Gen: run(project, loop)
  Gen-->>Ctrl: indices créés
  Ctrl->>Model: Project.avatars += nouveaux avatars
  Ctrl-->>View: indices + rafraîchissement TreeView
```

---

## 4) Hypothèses & limites
- Les classes marquées **[présumé]** sont déduites du périmètre fonctionnel *LMGC90_GUI* et de la doc LMGC90. Elles doivent être **confirmées par inspection du code** (`src/core/*.py`, `src/controllers/*.py`, `src/views/*.py`).
- Les signatures de méthodes indiquées reflètent les **exemples publics** (`add_material`, `generate_loop`) et les usages plausibles pour `save/load/export`. Une lecture complète permettrait d’étendre/ajuster les signatures.

---

## 5) Références
- Dépôt **LMG90_GUI_MVC** (structure, exemples de code et organisation MVC) : https://github.com/bzerourou/LMG90_GUI_MVC
- Dépôt **LMGC90_GUI** (périmètre fonctionnel de l’interface historique) : https://github.com/bzerourou/LMGC90_GUI
- Documentation **LMGC90** (architecture, préprocesseur/Chipy, Datbox) :
  - Page d’accueil doc : https://lmgc90.pages-git-xen.lmgc.univ-montp2.fr/lmgc90_dev/
  - Structure LMGC90 : https://lmgc90.pages-git-xen.lmgc.univ-montp2.fr/lmgc90_dev/dev_presentation.html

---

> Pour transformer ce fichier en **PNG/SVG/PDF**, utilisez par exemple *Mermaid* (support natif GitHub/GitLab/VS Code) ou `@mermaid-js/mermaid-cli` (`mmdc`).
