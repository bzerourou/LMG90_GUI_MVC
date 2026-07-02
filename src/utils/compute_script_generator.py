# ============================================================================
# compute_script_generator.py  —  LMGC90_GUI
# ============================================================================
"""
Genere le script de calcul chipy (command.py) a partir des parametres
"""

from io import StringIO
from pathlib import Path
from typing import Dict, Any

from ..core.particle_factory import BODY_COLLECTION_PICKLE, ParticleFactory


class ComputeScriptGenerator:
    """Genere le script command.py pour chipy."""

    _DEFAULTS: Dict[str, Any] = {
        'mhyp': 1, 'deformable': False, 'physics': 'MECAx',
        'Rloc_tol': 5e-2,
        'use_RBDY2': True,  'use_RBDY3': False,
        'use_DKDKx': True,  'use_DKJCx': False, 'use_DKKDx': False,
        'use_PLPLx': False, 'use_CLALp': False,  'use_ALpALp': False,
        'use_SPSPx': False, 'use_SPCDx': False,  'use_SPPLx': False,
        'use_CDCDx': False, 'use_CDPLx': False,  'use_PRPRx': False,
        'use_mecaFEM': False, 'use_therFEM': False, 'use_hydrFEM': False,
        'use_DKMECAx': False, 'use_ALpMECAx': False, 'use_SPMECAx': False,
        'use_PT2Dx': False,   'use_PT3Dx': False,
        'use_NODES': False,   'use_bulk_behav': False,
        'visu_RBDY2': True,  'visu_RBDY3': False,
        'visu_mecaFEM': False, 'visu_therFEM': False, 'visu_hydrFEM': False,
        'display_in_loop': True,
        'extract_Rnod': False, 'extract_Vloc': False, 'extract_Rloc': False,
        'extract_energy': False, 'extract_KE': False,
        'extract_fields': False, 'extract_internal': False,
        'vis_entries': [],
        'gbv2_entries': [],
        'gbv3_entries': [],
        'insp2d_entries': [],
        'insp3d_entries': [],
        'inspi_entries':  [],
        'use_restart': False, 'restart_step': 0,
        'use_stop_crit': False, 'stop_crit_type': 'energy',
        'stop_crit_val': 1e-6, 'stop_crit_freq': 10,
        'use_multi_step': False, 'multi_step_nb': 3,
        'multi_step_sizes': '1e-3, 1e-4, 1e-5',
        'dt': 1e-3, 'nb_steps': 1000, 'theta': 0.5,
        'tol': 1.666e-4, 'relax': 1.0, 'norm': 'Quad ',
        'gs_it1': 50, 'gs_it2': 1000,
        'solver_type': 'Stored_Delassus_Loops         ',
        'freq_write': 50, 'freq_display': 50,
        'disable_log': False,
    }

    _NO_ID_FUNCS = frozenset({
        'RBDY2_GetNbRBDY2', 'RBDY3_GetNbRBDY3',
        'RBDY2_KineticEnergy',
        'DISKx_GetNbDISKx', 'JONCx_GetNbJONCx',
        'POLYR_GetNbPOLYR', 'xKSID_GetNbxKSID',
        'SPHER_GetNbSPHER', 'POLYH_GetNbPOLYH',
        'CYLND_GetNbCYLND', 'PLANE_GetNbPLANE',
        'PT2Dx_GetNbPT2Dx', 'PT3Dx_GetNbPT3Dx',
        'DKDKx_GetNbDKDKx', 'DKJCx_GetNbDKJCx',
        'DKKDx_GetNbDKKDx', 'PLPLx_GetNbPLPLx',
        'CLALp_GetNbCLALp', 'ALpALp_GetNbALpALp',
        'SPSPx_GetNbSPSPx', 'SPCDx_GetNbSPCDx',
        'SPPLx_GetNbSPPLx', 'CDCDx_GetNbCDCDx',
        'CDPLx_GetNbCDPLx', 'PRPRx_GetNbPRPRx',
        'DKMECAx_GetNbDKMECAx', 'ALpMECAx_GetNbALpMECAx',
        'SPMECAx_GetNbSPMECAx',
    })

    def __init__(self, controller):
        self.controller = controller

    # =========================================================================
    # API publique
    # =========================================================================

    def generate(self, output_path: Path, params: Dict[str, Any]) -> None:
        """Ecrit command.py dans output_path."""
        output_path.write_text(self.generate_string(params), encoding='utf-8')

    def generate_string(self, params: Dict[str, Any]) -> str:
        """Retourne le script complet sous forme de chaine."""
        p   = {**self._DEFAULTS, **params}
        buf = StringIO()
        w   = buf.write

        # ── Factories ─────────────────────────────────────────────────────────
        # Les indices corps sont lus depuis body_collection.pkl (genere par
        # le script pre.py au moment de bodies.addAvatar), sur le modele
        # exemples/box_generation.py / box_simulation.py.
        _factory_active = []
        try:
            _fraw = getattr(self.controller.state, 'factories', None) or []
            if _fraw:
                _fengine = ParticleFactory.from_list_of_dicts(_fraw)
                _factory_active = [c for c in _fengine.configs if c.enabled]
        except Exception:
            _factory_active = []

        dim        = self.controller.state.dimension
        deformable = p['deformable']
        mhyp       = p['mhyp']

        use_RBDY2   = p['use_RBDY2']   and dim == 2
        use_RBDY3   = p['use_RBDY3']   and dim == 3
        use_mecaFEM = p['use_mecaFEM'] and deformable
        use_therFEM = p['use_therFEM'] and deformable
        use_hydrFEM = p['use_hydrFEM'] and deformable
        any_FEM     = use_mecaFEM or use_therFEM or use_hydrFEM

        tacts_2d = [t for t in ('DKDKx','DKJCx','DKKDx','PLPLx','CLALp','ALpALp') if p.get(f'use_{t}')]
        tacts_3d = [t for t in ('SPSPx','SPCDx','SPPLx','CDCDx','CDPLx','PRPRx')  if p.get(f'use_{t}')]
        tacts_mix = [t for t in ('DKMECAx','ALpMECAx','SPMECAx')                   if p.get(f'use_{t}')]
        tacts_pt  = [t for t in ('PT2Dx','PT3Dx','NODES')                           if p.get(f'use_{t}')]
        all_tacts = tacts_2d + tacts_3d + tacts_mix + tacts_pt

        use_multi   = p.get('use_multi_step', False)
        use_restart = p.get('use_restart', False)
        use_stop    = p.get('use_stop_crit', False)

        # Prefixe RBDY selon la dimension du projet (utilise pour les factories)
        _rbdy_prefix = 'RBDY2' if dim == 2 else 'RBDY3'

        # ── 1. En-tete ────────────────────────────────────────────────────────
        w('# -*- coding: utf-8 -*-\n')
        w('# Script de calcul genere automatiquement par LMGC90_GUI\n')
        w(f'# Projet    : {self.controller.state.name}\n')
        w(f'# Dimension : {dim}D\n')
        if _factory_active:
            w('#\n')
            w('# Particle Factories : indices corps via body_collection.pkl\n')
            w('# (genere par le script pre.py — cf. exemples/box_simulation.py)\n')
        w('\n')
        w('from pylmgc90 import chipy\n')
        if use_stop:
            w('import math\n')
        w('\n')

        # ── 2. Initialisation ─────────────────────────────────────────────────
        w('chipy.Initialize()\n')
        w('chipy.checkDirectories()\n')
        if p.get('disable_log'):
            w('chipy.utilities_DisableLogMes()\n')
        w('\n')

        # ── 3. Parametres ─────────────────────────────────────────────────────
        w('# ── Parametres generaux ──────────────────────────────────────\n')
        w(f'dim    = {dim}\n')
        w(f'mhyp   = {mhyp}\n')
        w('\n')
        w(f'dt          = {p["dt"]!r}\n')
        w(f'nb_steps    = {p["nb_steps"]}\n')
        w(f'theta       = {p["theta"]!r}\n')
        w('\n')
        w(f'Rloc_tol    = {p["Rloc_tol"]!r}\n')
        w('\n')
        w(f'tol         = {p["tol"]!r}\n')
        w(f'relax       = {p["relax"]!r}\n')
        w(f'norm        = {p["norm"]!r}\n')
        w(f'gs_it1      = {p["gs_it1"]}\n')
        w(f'gs_it2      = {p["gs_it2"]}\n')
        w(f'solver_type = {p["solver_type"]!r}\n')
        w('\n')
        w(f'freq_write   = {p["freq_write"]}\n')
        w(f'freq_display = {p["freq_display"]}\n')
        w('\n')

        if use_multi:
            sizes_str = p.get('multi_step_sizes', '1e-3')
            nb_phases  = p.get('multi_step_nb', 3)
            w('# Multi-pas : sequence de pas de temps\n')
            w(f'dt_sequence      = [{sizes_str}]\n')
            w(f'steps_per_phase  = nb_steps // {nb_phases}\n')
            w('\n')

        if use_stop:
            w("# Critere d'arret\n")
            w(f'stop_tol  = {p["stop_crit_val"]!r}\n')
            w(f'stop_freq = {p["stop_crit_freq"]}\n')
            w('\n')

        # ── 4. Configuration chipy ────────────────────────────────────────────
        w('# ── Configuration ───────────────────────────────────────────\n')
        w('chipy.SetDimension(dim, mhyp)\n')
        w("chipy.utilities_logMes('INIT TIME STEPPING')\n")
        w('chipy.TimeEvolution_SetTimeStep(dt)\n')
        w('chipy.Integrator_InitTheta(theta)\n')
        w('\n')
        w(f'chipy.ReadDatbox(deformable={deformable})\n')
        w('\n')

        if p.get('disable_log'):
            w('chipy.utilities_DisableLogMes()\n')
            w('\n')

        # ── 5. Ouverture fichiers sortie ──────────────────────────────────────
        w("chipy.utilities_logMes('DISPLAY & WRITE')\n")
        w('chipy.OpenDisplayFiles()\n')
        w('chipy.OpenPostproFiles()\n')
        w('\n')

        # ── 6. Masse ──────────────────────────────────────────────────────────
        w("chipy.utilities_logMes('COMPUTE MASS')\n")
        w('chipy.ComputeMass()\n')
        if use_mecaFEM:
            w('chipy.mecaFEMx_ComputeMass()\n')
        if use_therFEM:
            w('chipy.therFEMx_ComputeMass()\n')
        if use_hydrFEM:
            w('chipy.hydrFEMx_ComputeMass()\n')
        w('\n')

        # ── Helpers locaux ────────────────────────────────────────────────────

        def _resolve_group_ids(grp_name: str):
            """
            Retourne les numéros de corps LMGC90 (1-based, en chaînes) pour
            les avatars du groupe donné.

            avatar_groups contient désormais des avatar_ids (str) et non plus
            des positions entières.  On résout chaque id vers sa position
            courante dans state.avatars, puis on ajoute 1 pour obtenir le
            numéro LMGC90.
            """
            if not grp_name or self.controller is None:
                return []
            state = getattr(self.controller, 'state', None)
            if state is None:
                return []
            groups     = getattr(state, 'avatar_groups', {}) or {}
            avatar_ids = groups.get(grp_name, [])
            if not avatar_ids:
                return []
            # Construire le mapping id → index en une seule passe
            id_to_idx = {av.avatar_id: i for i, av in enumerate(state.avatars)}
            return [str(id_to_idx[aid] + 1) for aid in avatar_ids if aid in id_to_idx]

        def _timing_guard(entry: dict):
            mode = entry.get('step_mode', '')
            if not mode:
                freq = int(entry.get('freq', 1))
                mode = 'every_n' if freq > 1 else 'all'
            val = int(entry.get('step_val', entry.get('freq', 1)))
            if mode == 'every_n' and val > 1:
                return ind + 'if k % {} == 0:\n'.format(val), ind + '    '
            if mode == 'at_k':
                return ind + 'if k == {}:\n'.format(val), ind + '    '
            return '', ind

        def _is_no_id_func(func_name: str) -> bool:
            if func_name in self._NO_ID_FUNCS:
                return True
            if 'GetNb' in func_name:
                return True
            return False

        def _write_vis_before(entry: dict) -> None:
            action   = entry.get('action', 'visible')
            edim     = entry.get('dim', '2D')
            ids_str  = entry.get('ids', '').strip()
            grp_name = entry.get('group', '').strip()
            id_list  = (
                [t.strip() for t in ids_str.split(',') if t.strip().isdigit()]
                if ids_str else _resolve_group_ids(grp_name)
            )
            suffix = '_SetVisible' if action == 'visible' else '_SetInvisible'
            func   = ('RBDY2' if edim == '2D' else 'RBDY3') + suffix
            for av_id in id_list:
                w('chipy.{}({})\n'.format(func, av_id))

        def _emit_vis_entry(entry: dict, in_loop_context: bool = False) -> None:
            action   = entry.get('action', 'visible')
            edim     = entry.get('dim', '2D')
            ids_str  = entry.get('ids', '').strip()
            grp_name = entry.get('group', '').strip()
            if ids_str:
                id_list = [t.strip() for t in ids_str.split(',') if t.strip().isdigit()]
            elif grp_name:
                id_list = _resolve_group_ids(grp_name)
            else:
                return
            suffix = '_SetVisible' if action == 'visible' else '_SetInvisible'
            func   = ('RBDY2' if edim == '2D' else 'RBDY3') + suffix
            if in_loop_context:
                guard, xi = _timing_guard(entry)
                if guard:
                    w(guard)
                    for av_id in id_list:
                        w(xi + 'chipy.{}({})\n'.format(func, av_id))
                else:
                    for av_id in id_list:
                        w(ind + 'chipy.{}({})\n'.format(func, av_id))
            else:
                for av_id in id_list:
                    w('chipy.{}({})\n'.format(func, av_id))

        def _emit_gbv(entry: dict, func_name: str) -> None:
            vec     = entry.get('vec', 'Coor_')
            ids_str = entry.get('ids', '').strip()
            grp     = entry.get('group', '').strip()
            id_list = (
                [t.strip() for t in ids_str.split(',') if t.strip().isdigit()]
                if ids_str else _resolve_group_ids(grp)
            )
            if not id_list:
                return
            ids_repr = '[{}]'.format(', '.join(id_list))
            guard, xi = _timing_guard(entry)
            if guard:
                w(guard)
                w(xi + 'for _id in {}:\n'.format(ids_repr))
                w(xi + "    chipy.{}('{}', _id)\n".format(func_name, vec))
            else:
                w(xi + 'for _id in {}:\n'.format(ids_repr))
                w(xi + "    chipy.{}('{}', _id)\n".format(func_name, vec))
            w('\n')

        def _emit_insp(entry: dict) -> None:
            func    = entry.get('func', '')
            ids_str = entry.get('ids', '').strip()
            grp     = entry.get('group', '').strip()
            store   = entry.get('store', '').strip()
            if not func:
                return
            no_id = _is_no_id_func(func) or (not ids_str and not grp)
            guard, extra_ind = _timing_guard(entry)
            if no_id:
                call_str = 'chipy.{}()'.format(func)
                line     = '{} = {}'.format(store, call_str) if store else call_str
                if guard:
                    w(guard)
                    w(extra_ind + line + '\n')
                else:
                    w(ind + line + '\n')
            else:
                id_list = (
                    [t.strip() for t in ids_str.split(',') if t.strip().isdigit()]
                    if ids_str else _resolve_group_ids(grp)
                )
                if not id_list:
                    return
                ids_repr = '[{}]'.format(', '.join(id_list))
                inner = (
                    '    {}_{{_id}} = chipy.{}(_id)\n'.format(store, func)
                    if store
                    else '    chipy.{}(_id)\n'.format(func)
                )
                if guard:
                    w(guard)
                    w(extra_ind + 'for _id in {}:\n'.format(ids_repr))
                    w(extra_ind + '    ' + inner.lstrip())
                else:
                    w(ind + 'for _id in {}:\n'.format(ids_repr))
                    w(ind + inner)
            w('\n')

        def _is_in_loop(e: dict) -> bool:
            mode = e.get('step_mode', '')
            return (mode != 'after') if mode else e.get('in_loop', True)

        # ── 6b. Visibilite des avatars avant la boucle ────────────────────────
        _vis_before  = [e for e in p.get('vis_entries', []) if not e.get('step_mode')]
        _vis_in_loop = [
            e for e in p.get('vis_entries', [])
            if e.get('step_mode') and e.get('step_mode') != 'after'
        ]
        _vis_after = [
            e for e in p.get('vis_entries', [])
            if e.get('step_mode') == 'after'
        ]

        for _ve in _vis_before:
            _write_vis_before(_ve)
        if _vis_before:
            w('\n')

        # ── 6c. Particle Factories : pickle + invisibilite + planning ───────────
        #
        # Pattern box_simulation.py :
        #   1. Charger body_collection.pkl (ecrit par pre.py apres addAvatar)
        #   2. SetInvisible sur tous les corps factory
        #   3. Construire _factory_schedule = {k: [ids]} depuis les vagues
        #   4. Dans la boucle : SetVisible aux pas planifies
        #
        if _factory_active:
            w('# ============================================================\n')
            w('# Particle Factories — body_collection.pkl\n')
            w('# ============================================================\n')
            w('import pickle\n')
            w('import os\n')
            w(f"_pkl_path = '{BODY_COLLECTION_PICKLE}'\n")
            w("if not os.path.isfile(_pkl_path):\n")
            w("    raise FileNotFoundError(\n")
            w(f"        f\"Fichier '{{_pkl_path}}' introuvable. \"\n")
            w("        \"Executez d'abord le script pre.py (generation DATBOX) \"\n")
            w("        \"pour creer body_collection.pkl.\")\n")
            w("with open(_pkl_path, 'rb') as _pkl_f:\n")
            w("    body_collection = pickle.load(_pkl_f)\n")
            w("print('Charge', _pkl_path, '—', body_collection.get('total_nb_bodies', '?'), 'corps')\n")
            w('\n')

            w('# Masquer toutes les particules de factory au depart\n')
            w("for _fcfg in body_collection.get('factories', {}).values():\n")
            w("    if not _fcfg.get('enabled', True):\n")
            w("        continue\n")
            w(f"    for _bnum in _fcfg['body_numbers']:\n")
            w(f"        chipy.{_rbdy_prefix}_SetInvisible(_bnum)\n")
            w('\n')

            w("# Planning d'activation : {k: [ids_corps_a_rendre_visibles]}\n")
            w('_factory_schedule: dict = {}\n')
            w("for _fname, _fcfg in body_collection.get('factories', {}).items():\n")
            w("    if not _fcfg.get('enabled', True):\n")
            w("        continue\n")
            w("    _nums = _fcfg['body_numbers']\n")
            w("    _bs   = _fcfg['batch_size']\n")
            w("    _ss   = _fcfg['start_step']\n")
            w("    _iv   = _fcfg['interval_steps']\n")
            w("    _nb   = (len(_nums) + _bs - 1) // _bs\n")
            w("    for _bi in range(_nb):\n")
            w("        _k = _ss + _bi * _iv\n")
            w("        _batch = _nums[_bi * _bs : (_bi + 1) * _bs]\n")
            w("        _factory_schedule.setdefault(_k, []).extend(_batch)\n")
            w('\n')

        # ── 7. Restart ────────────────────────────────────────────────────────
        if use_restart:
            w('# ── Restart ─────────────────────────────────────────────\n')
            w('chipy.ReadIni()\n')
            w(f'chipy.SetStep({p["restart_step"]})\n')
            w('\n')

        # ── 8. Boucle(s) de calcul ────────────────────────────────────────────
        if use_multi:
            w('# ── Boucle multi-pas ────────────────────────────────────\n')
            w('for _phase, _dt in enumerate(dt_sequence):\n')
            w('    chipy.TimeEvolution_SetTimeStep(_dt)\n')
            w("    chipy.utilities_logMes(f'PHASE {_phase + 1} / {len(dt_sequence)} - dt = {_dt}')\n")
            w('    for k in range(steps_per_phase):\n')
            ind = '        '
        else:
            w('# ── Boucle de calcul ─────────────────────────────────────\n')
            w('for k in range(nb_steps):\n')
            ind = '    '

        def L(line: str) -> None:
            w(ind + line + '\n')

        L("chipy.utilities_logMes('INCREMENT STEP')")
        L('chipy.IncrementStep()')
        w('\n')

        # ── 8a. Activation des vagues de factory dans la boucle ───────────────
        if _factory_active:
            L('# ── Particle Factory : activation des vagues planifiees ───')
            L('if k in _factory_schedule:')
            w(ind + '    for _bnum in _factory_schedule[k]:\n')
            w(ind + f'        chipy.{_rbdy_prefix}_SetVisible(_bnum)\n')
            w('\n')

        # a. FreeVelocity corps rigides
        if use_RBDY2:
            L("chipy.utilities_logMes('COMPUTE Fext/Fint - RBDY2')")
            L('chipy.ComputeFext()')
            L('chipy.ComputeBulk()')
            L("chipy.utilities_logMes('COMPUTE Free Velocity - RBDY2')")
            L('chipy.ComputeFreeVelocity()')
        if use_RBDY3:
            L("chipy.utilities_logMes('COMPUTE Free Velocity - RBDY3')")
            L('chipy.RBDY3_NewStep()')
            L('chipy.RBDY3_FreeVelocity()')
        w('\n')

        # b. FreeVelocity deformables
        if use_mecaFEM:
            L("chipy.utilities_logMes('mecaFEMx - assembly + FreeVelocity')")
            L('chipy.mecaFEMx_ComputeFext()')
            L('chipy.mecaFEMx_ComputeBulk()')
            L('chipy.mecaFEMx_ComputeFreeVelocity()')
        if use_therFEM:
            L("chipy.utilities_logMes('therFEMx - flux + FreeVelocity')")
            L('chipy.therFEMx_ComputeFext()')
            L('chipy.therFEMx_ComputeBulk()')
            L('chipy.therFEMx_ComputeFreeVelocity()')
        if use_hydrFEM:
            L("chipy.utilities_logMes('hydrFEMx - pression + FreeVelocity')")
            L('chipy.hydrFEMx_ComputeFext()')
            L('chipy.hydrFEMx_ComputeBulk()')
            L('chipy.hydrFEMx_ComputeFreeVelocity()')
        if any_FEM:
            w('\n')

        # c. Detection de contact
        L("chipy.utilities_logMes('SELECT PROX TACTORS')")
        if all_tacts:
            for t in tacts_2d:
                L(f'chipy.{t}_SelectProxTactors()')
            for t in tacts_3d:
                L(f'chipy.{t}_SelectProxTactors()')
            for t in tacts_mix:
                L(f'chipy.{t}_SelectProxTactors()')
            for t in tacts_pt:
                L(f'chipy.{t}_SelectProxTactors()')
        else:
            L('chipy.SelectProxTactors()')
        w('\n')

        # d. Resolution
        L("chipy.utilities_logMes('RESOLUTION')")
        L('chipy.RecupRloc(Rloc_tol)')
        L('chipy.ExSolver(solver_type, norm, tol, relax, gs_it1, gs_it2)')
        L('chipy.UpdateTactBehav()')
        L('chipy.StockRloc()')
        w('\n')

        # e. Comportement volumique
        if p.get('use_bulk_behav'):
            L("chipy.utilities_logMes('UPDATE BULK BEHAV')")
            L('chipy.UpdateBulkBehav()')
            w('\n')

        # f. ComputeDof + UpdateStep
        L("chipy.utilities_logMes('COMPUTE DOF')")
        L('chipy.ComputeDof()')
        if use_mecaFEM:
            L('chipy.mecaFEMx_ComputeDof()')
        if use_therFEM:
            L('chipy.therFEMx_ComputeDof()')
        if use_hydrFEM:
            L('chipy.hydrFEMx_ComputeDof()')
        w('\n')
        L("chipy.utilities_logMes('UPDATE DOF')")
        L('chipy.UpdateStep()')
        if use_mecaFEM:
            L('chipy.mecaFEMx_UpdateStep()')
        if use_therFEM:
            L('chipy.therFEMx_UpdateStep()')
        if use_hydrFEM:
            L('chipy.hydrFEMx_UpdateStep()')
        w('\n')

        # g. Extraction
        if p.get('extract_energy'):
            L('chipy.ComputeEnergy()')
            L('chipy.WriteEnergy()')
        if p.get('extract_KE') and use_RBDY2:
            L('chipy.RBDY2_KineticEnergy()')
        if p.get('extract_Rnod'):
            L('chipy.inter_handler_Rnod()')
        if p.get('extract_Vloc'):
            L('chipy.inter_handler_Vloc()')
        if p.get('extract_Rloc'):
            L('chipy.inter_handler_Rloc()')
        if p.get('extract_fields') and use_mecaFEM:
            L('chipy.mecaFEMx_WriteBodies(freq_write)')
        if p.get('extract_internal') and use_mecaFEM:
            L('chipy.mecaFEMx_WriteInternalVariables(freq_write)')
        if any(p.get(k) for k in (
            'extract_energy', 'extract_KE', 'extract_Rnod',
            'extract_Vloc',   'extract_Rloc',
            'extract_fields', 'extract_internal',
        )):
            w('\n')

        # ── GetBodyVector RBDY2 / RBDY3 dans la boucle ───────────────────────
        for _gbv_key, _gbv_func, _gbv_flag in [
            ('gbv2_entries', 'RBDY2_GetBodyVector', use_RBDY2),
            ('gbv3_entries', 'RBDY3_GetBodyVector', use_RBDY3),
        ]:
            if not _gbv_flag:
                continue
            _in_entries = [
                e for e in p.get(_gbv_key, [])
                if e.get('step_mode', '') != 'after'
                and (e.get('step_mode') or e.get('in_loop', True))
            ]
            if _in_entries:
                L("chipy.utilities_logMes('{} extraction')".format(_gbv_func))
                for _e in _in_entries:
                    _emit_gbv(_e, _gbv_func)

        # ── Visibilite dans la boucle ─────────────────────────────────────────
        for _ve_loop in _vis_in_loop:
            _emit_vis_entry(_ve_loop, in_loop_context=True)

        # ── Inspection contacteurs / interactions (dans la boucle) ────────────
        _all_insp_in = (
            [e for e in p.get('insp2d_entries', []) if _is_in_loop(e)]
            + [e for e in p.get('insp3d_entries', []) if _is_in_loop(e)]
            + [e for e in p.get('inspi_entries',  []) if _is_in_loop(e)]
        )
        if _all_insp_in:
            L("chipy.utilities_logMes('INSPECTION')")
            for _ei in _all_insp_in:
                _emit_insp(_ei)

        # h. Critere d'arret
        if use_stop:
            L("# Critere d'arret")
            L('if k % stop_freq == 0:')
            stop_type = p.get('stop_crit_type', 'energy')
            if stop_type == 'energy':
                w(ind + '    _crit = chipy.GetResidualEnergy()\n')
            elif stop_type == 'disp_max':
                w(ind + '    _crit = chipy.GetMaxDisplacement()\n')
            else:
                w(ind + '    _crit = chipy.GetForceResidual()\n')
            w(ind + '    if _crit < stop_tol:\n')
            w(ind + "        chipy.utilities_logMes(\n")
            w(ind + "            f'Critere atteint a k={k} : {_crit:.4e} < {stop_tol:.2e}')\n")
            w(ind + '        break\n')
            w('\n')

        # i. Ecriture resultats
        L("chipy.utilities_logMes('WRITE OUT')")
        L('chipy.WriteOut(freq_write)')
        if use_RBDY3:
            L('chipy.RBDY3_WriteOut(freq_write)')
        w('\n')

        # Visualisation dans la boucle
        if p.get('display_in_loop', True):
            L("chipy.utilities_logMes('VISU & POSTPRO')")
            wrote_visu = False
            if p.get('visu_RBDY2') and use_RBDY2:
                L('chipy.WriteDisplayFiles(freq_display)')
                wrote_visu = True
            if p.get('visu_RBDY3') and use_RBDY3:
                L('chipy.WriteDisplayFiles(freq_display)')
                wrote_visu = True
            if p.get('visu_mecaFEM') and use_mecaFEM:
                L('chipy.mecaFEMx_WriteDisplayFiles(freq_display)')
                wrote_visu = True
            if p.get('visu_therFEM') and use_therFEM:
                L('chipy.therFEMx_WriteDisplayFiles(freq_display)')
                wrote_visu = True
            if p.get('visu_hydrFEM') and use_hydrFEM:
                L('chipy.hydrFEMx_WriteDisplayFiles(freq_display)')
                wrote_visu = True
            if not wrote_visu:
                L('chipy.WriteDisplayFiles(freq_display)')
            L('chipy.WritePostproFiles()')
            w('\n')

        # ── GetBodyVector hors boucle (step_mode='after') ────────────────────
        for _gbv_key2, _gbv_func2, _gbv_flag2 in [
            ('gbv2_entries', 'RBDY2_GetBodyVector', use_RBDY2),
            ('gbv3_entries', 'RBDY3_GetBodyVector', use_RBDY3),
        ]:
            if not _gbv_flag2:
                continue
            _out_entries = [
                e for e in p.get(_gbv_key2, [])
                if e.get('step_mode', '') == 'after'
                or (not e.get('step_mode') and not e.get('in_loop', True))
            ]
            if _out_entries:
                w('# ── {} hors boucle ──────\n'.format(_gbv_func2))
                for _e2 in _out_entries:
                    _v2  = _e2.get('vec', 'Coor_')
                    _s2  = _e2.get('ids', '').strip()
                    _g2  = _e2.get('group', '').strip()
                    _il2 = (
                        [t.strip() for t in _s2.split(',') if t.strip().isdigit()]
                        if _s2 else _resolve_group_ids(_g2)
                    )
                    if _il2:
                        w('for _id in [{}]:\n'.format(', '.join(_il2)))
                        w("    chipy.{}('{}', _id)\n".format(_gbv_func2, _v2))
                        w('\n')

        # ── Inspection hors boucle ────────────────────────────────────────────
        _all_insp_out = (
            [e for e in p.get('insp2d_entries', []) if not _is_in_loop(e)]
            + [e for e in p.get('insp3d_entries', []) if not _is_in_loop(e)]
            + [e for e in p.get('inspi_entries',  []) if not _is_in_loop(e)]
        )
        if _all_insp_out:
            w('# ── Inspection hors boucle ──────\n')
            for _eo in _all_insp_out:
                _func_o  = _eo.get('func', '')
                _ids_o   = _eo.get('ids', '').strip()
                _grp_o   = _eo.get('group', '').strip()
                _store_o = _eo.get('store', '').strip()
                if not _func_o:
                    continue
                if _is_no_id_func(_func_o) or (not _ids_o and not _grp_o):
                    if _store_o:
                        w('{} = chipy.{}()\n'.format(_store_o, _func_o))
                    else:
                        w('chipy.{}()\n'.format(_func_o))
                else:
                    _il_o = (
                        [t.strip() for t in _ids_o.split(',') if t.strip().isdigit()]
                        if _ids_o else _resolve_group_ids(_grp_o)
                    )
                    if _il_o:
                        w('for _id in [{}]:\n'.format(', '.join(_il_o)))
                        if _store_o:
                            w('    {}_{{_id}} = chipy.{}(_id)\n'.format(_store_o, _func_o))
                        else:
                            w('    chipy.{}(_id)\n'.format(_func_o))
                w('\n')

        # ── Visibilite apres boucle (step_mode='after') ──────────────────────
        if _vis_after:
            w('# ── Visibilite apres boucle ──────\n')
            for _ve_after in _vis_after:
                _emit_vis_entry(_ve_after, in_loop_context=False)
            w('\n')

        # ── 9. Visualisation hors-boucle ──────────────────────────────────────
        if not p.get('display_in_loop', True):
            w('# ── Visualisation finale (hors boucle) ──────────────────\n')
            if p.get('visu_RBDY2') and use_RBDY2:
                w('chipy.RBDY2_WriteDisplayFiles(1)\n')
            if p.get('visu_RBDY3') and use_RBDY3:
                w('chipy.RBDY3_WriteDisplayFiles(1)\n')
            if p.get('visu_mecaFEM') and use_mecaFEM:
                w('chipy.mecaFEMx_WriteDisplayFiles(1)\n')
            if p.get('visu_therFEM') and use_therFEM:
                w('chipy.therFEMx_WriteDisplayFiles(1)\n')
            if p.get('visu_hydrFEM') and use_hydrFEM:
                w('chipy.hydrFEMx_WriteDisplayFiles(1)\n')
            w('chipy.WritePostproFiles()\n')
            w('\n')

        # ── 10. Finalisation ──────────────────────────────────────────────────
        w('chipy.CloseDisplayFiles()\n')
        w('chipy.ClosePostproFiles()\n')
        w('chipy.Finalize()\n')
        w('\n')
        w("print('CALCUL TERMINE')\n")

        return buf.getvalue()