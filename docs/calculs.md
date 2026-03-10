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
| `solver_type` | Solveur | `NLGS` | Type de solveur (`NLGS`, `MULTIGRID`, etc.) |
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




