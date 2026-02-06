# Conditions aux limites (DOF)

Application de conditions aux limites ( déplacements ou vitesses imposés) sur vos avatars.

## Interface
- Vous pouvez sélectionner un avatar ou un **groupe** d'avatars
- Action : translate, rotate, imposeDrivenDof, imposeInitValue

## Paramètres
### `translate(dx=0., dy=0., dz=0.)`
Translate (déplace) tous les nœuds de l'avatar selon un vecteur de translation.
| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `dx` | float | 0.0 | Translation selon l'axe x (m) |
| `dy` | float | 0.0 | Translation selon l'axe y (m) |
| `dz` | float | 0.0 | Translation selon l'axe z (m) |


### `rotate(description='Euler', phi=0., theta=0., psi=0., alpha=0., axis=[0.,0.,1.], center=[0.,0.,0.])`
**Description** : Applique une rotation à l'avatar autour d'un centre donné, soit par angles d'Euler, soit par axe-angle.

**Paramètres** :
| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `description` | str | 'Euler' | Type de rotation : `'Euler'` ou `'axis'` |
| `phi` | float | 0.0 | 1er angle d'Euler - rotation autour de z (rad) |
| `theta` | float | 0.0 | 2ème angle d'Euler - rotation autour de x (rad) |
| `psi` | float | 0.0 | 3ème angle d'Euler - rotation autour de z (rad) |
| `alpha` | float | 0.0 | Angle de rotation (pour mode 'axis') (rad) |
| `axis` | list[3] | [0,0,1] | Axe de rotation (pour mode 'axis') |
| `center` | list[3] | [0,0,0] | Centre de rotation (m) |

#### Mode 1 : Angles d'Euler (`description='Euler'`)
Rotation définie par 3 rotations successives :
1. Rotation `phi` autour de z
2. Rotation `theta` autour de x
3. Rotation `psi` autour de z

#### Mode 2 : Axe-Angle (`description='axis'`)
Rotation d'un angle `alpha` autour d'un axe donné.

### `imposeDrivenDof(group='all', component=1, description='predefined', ct=0., amp=0., omega=0., phi=0., rampi=1., ramp=0., evolutionFile='', dofty='temp')`

**Description** : Impose une condition aux limites pilotée (Driven DOF) sur les nœuds d'un groupe. La valeur peut être constante, sinusoïdale, avec rampe, ou définie par un fichier.

**Paramètres** :
| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `group` | str | 'all' | Nom du groupe de nœuds concernés |
| `component` | int ou list | 1 | Composante(s) du DDL (≥1) |
| `description` | str | 'predefined' | Type : `'predefined'` ou `'evolution'` |
| `dofty` | str | 'temp' | Type de DDL : `'vlocy'`, `'force'`, `'temp'`, `'flux'` |
| `ct` | float | 0.0 | Valeur constante |
| `amp` | float | 0.0 | Amplitude du cosinus |
| `omega` | float | 0.0 | Pulsation (rad/s) |
| `phi` | float | 0.0 | Phase du cosinus (rad) |
| `rampi` | float | 1.0 | Valeur initiale de la rampe |
| `ramp` | float | 0.0 | Pente de la rampe |
| `evolutionFile` | str | '' | Fichier d'évolution temporelle |

**Types de DDL (`dofty`)** :
- **MECAx** : `'vlocy'` (vitesse), `'force'` (force)
- **THERx** : `'temp'` (température), `'flux'` (flux thermique)
- **POROx** : `'vlocy'`, `'force'`
- **MULTI** : `'prim_'` (primaire), `'dual_'` (dual)

**Formule générale (mode 'predefined')** :

f(t) = [ct + amp·cos(ω·t + φ)] × sign(rampi + ramp·t) × min(|rampi + ramp·t|, 1)

## Support des groupes
Tous les groupes (boucles, granulométrie) apparaissent dans la liste

## Exemple
Vous pouvez ouvrir l'exemple de bielle-manivelle fournit dans les exemples, 'slider_crank.lmgc90' dans lequel on applique quatre différents DOFs sur les avatars du modèles, 




![](captures/exemple_slider_crank.JPG)
