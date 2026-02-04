# Création d'un Matériau

Cette section explique comment créer et configurer un matériau dans LMGC90_GUI.

## Interface
- Onglet **Matériau** vous sert à créer votre matériau,
- Champs principaux :
  - **Nom** : Nom unique du matériau (maximum 5 caractère ex: `TDURx`, `ROCKx`, `steel`)
  - **Type** : Liste déroulante avec les types supportés
  - **Densité** : Valeur en kg/m³ (en SI)
  - **Propriétés** : Champ texte pour paramètres avancés pour chaque type de matériau

## Types de matériaux disponibles
Vous pourriez créer différents types de matériaux, ceux qui sont inclus sont :
- **RIGID** : Corps rigide (densité obligatoire)
- **ELAS** : Élastique linéaire isotrope par défaut
- **ELAS_DILA** : Élastique avec dilatation thermique
- **VISCO_ELAS** : Viscoélastique
- **ELAS_PLAS** : Élastoplastique
- **THERMO_ELAS** : Thermoélastique
- **PORO_ELAS** : Poroélastique

## Exemple de création
**LMGC90_GUI** vous proposera comme d'habitude des valeurs par défaut pour le nom, type et densité,  
1. Sélectionnez le type (ex: ELAS), 
2. LMGC90_GUI vous chargera automatiquement les paramètres de ce matériau, il vous suffira seulement de modifier les valeurs dans le champs propriétés  (ex acier):
   - elas='standard', young=200e+9, nu=0.3, anisotropy='isotropic' 
3. Cliquez ensuite sur bouton **Créer Matériau**

![matériaux](captures/materiau_steel.JPG)


## Astuces
- Le champ Propriétés accèpte la syntaxe Python-like
- Utilisez les variables dynamiques si définies (menu Outils -> définir variables dynamiques)
- Faites attention aux matériaux choisis pour les éléments rigides du code LMGC90

## Modification/suppression
Vous avez aussi la possibilité de modifier ou de supprimer un matériau, pour cela sur le tabelau de liste des matériaux crées , commencez par sélectionner un avatar, cliquez ensuite sur le bouton "modifier sélection"  toutes ses données seront chargés ensuit en mode _"Edition"_ 
![](captures/materiau_steel_modification.JPG)

il vous suffit seulement de modifier vos nouvelles valeurs , puis d'enregistrer les modifications, 

