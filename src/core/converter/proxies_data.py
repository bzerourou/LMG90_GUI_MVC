"""Proxies pour matériaux, modèles, lois de contact, visibilité, postpro, granulo."""
import numpy as np


class _MaterialObj:
    def __init__(self, name, materialType='RIGID', density=1000., **props):
        self.name          = name
        self.material_type = materialType
        self.density       = float(density)
        self.props         = dict(props)

    def __repr__(self): return f"Material({self.name})"


class _ModelObj:
    def __init__(self, name, physics='MECAx', element='Rxx2D', dimension=2, **opts):
        self.name      = name
        self.physics   = physics
        self.element   = element
        self.dimension = int(dimension)
        self.opts      = dict(opts)

    def __repr__(self): return f"Model({self.name})"


class _TactBehavObj:
    def __init__(self, name, law, fric=None, **props):
        self.name  = name
        self.law   = law
        self.fric  = fric
        self.props = dict(props)


class _SeeTableObj:
    def __init__(self, CorpsCandidat, candidat, colorCandidat,
                 CorpsAntagoniste, antagoniste, colorAntagoniste,
                 behav, alert=0.1, **kw):
        self.candidate_body       = CorpsCandidat
        self.candidate_contactor  = candidat
        self.candidate_color      = colorCandidat
        self.antagonist_body      = CorpsAntagoniste
        self.antagonist_contactor = antagoniste
        self.antagonist_color     = colorAntagoniste
        self.behav_name = (behav.name if isinstance(behav, _TactBehavObj) else str(behav))
        self.alert      = float(alert)


class _PostproCommandObj:
    def __init__(self, name, step=1, rigid_set=None, **kw):
        self.name      = name
        self.step      = int(step)
        self.rigid_set = rigid_set


class _GranuloRadii:
    """Tableau de rayons retourne par granulo_Random."""
    def __init__(self, nb, rmin, rmax, seed=None):
        self.nb   = nb
        self.rmin = rmin
        self.rmax = rmax
        self.seed = seed
        rng        = np.random.default_rng(seed)
        self._arr  = rng.uniform(rmin, rmax, nb)
        self._granulo_idx = None

    def __len__(self):              return len(self._arr)
    def __getitem__(self, idx):     return self._arr[idx]
    def __setitem__(self, idx, v):  self._arr[idx] = v

    @property
    def size(self): return self._arr.size