# Lois de Contact

Définition des interactions entre vos avatars.

## Lois disponibles
Liste de types d'inetractions qui sont implémentées : 
- IQS_CLB (frottement de Coulomb)
- IQS_CLB_g0 (frottement de Coulomb avec une distance de départ)
- COUPLED_DOF (liaison parfaite)
- IQS_DS_CLB  (frottement statique et dynamique)                 
- IQS_MOHR_DS_CLB (contact de Mohr)         
- IQS_MAC_CZM  (collage)                
- ELASTIC_WIRE (fil élastique)              
- ELASTIC_REPELL_CLB (barre élastique)

## Paramètres
- Nom : chaine de cinq caractères
- Fric (pour IQS_CLB ou IQS_CLB_g0, IQS_DS_CLB )


## Exemple 
 


## Utilisation typique
- COUPLED_DOF pour joints mécaniques
- IQS_CLB pour contacts frottants

