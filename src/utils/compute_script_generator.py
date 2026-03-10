# ============================================================================
# compute_script_generator.py  —  LMGC90_GUI
# ============================================================================
"""
Genere le script de calcul chipy (command.py) a partir des parametres
collectes par ComputeTab.get_parameters() fusionnes avec
ChipyRoutinesDialog.get_params().

Structure du script genere :
  1.  Imports  +  initialisation
  2.  Parametres (dt, theta, solveur, …)
  3.  chipy.SetDimension(dim, mhyp)
  4.  ReadDatbox(deformable=…)
  5.  Ouverture fichiers de sortie
  6.  ComputeMass  (+  mecaFEMx_ComputeMass)
  7.  Restart eventuel  (ReadIni + SetStep)
  8.  Boucle de calcul  (simple ou multi-pas) :
        a. IncrementStep
        b. FreeVelocity  —  RBDY2 / RBDY3 / mecaFEMx / therFEMx / hydrFEMx
        c. SelectProxTactors  —  tous les detecteurs actifs
        d. RecupRloc / ExSolver / UpdateTactBehav / StockRloc
        e. UpdateBulkBehav  (si coche)
        f. ComputeDof  +  UpdateStep  (+  variantes FEM)
        g. Extraction  (energie, forces, champs)
        h. Critere d'arret  (si active)
        i. WriteOut  +  WriteDisplayFiles  +  WritePostproFiles
  9.  Visualisation hors-boucle  (si display_in_loop = False)
  10. CloseDisplayFiles / ClosePostproFiles / Finalize
"""

from io import StringIO
from pathlib import Path
from typing import Dict, Any


class ComputeScriptGenerator:
    """Genere le script command.py pour chipy."""

    # Valeurs par defaut — meme structure que ChipyRoutinesDialog.DEFAULTS
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
        # Visibilite avatars
        'vis_RBDY2_visible': '', 'vis_RBDY2_invisible': '',
        'vis_RBDY3_visible': '', 'vis_RBDY3_invisible': '',
        # GetBodyVector RBDY2
        'gbv2_Coor': False,          'gbv2_Coor_freq': 1,
        'gbv2_Velo': False,          'gbv2_Velo_freq': 1,
        'gbv2_Fext': False,          'gbv2_Fext_freq': 1,
        'gbv2_Reac': False,          'gbv2_Reac_freq': 1,
        'gbv2_Acce': False,          'gbv2_Acce_freq': 1,
        'gbv2_RigidBodyMass': False, 'gbv2_RigidBodyMass_freq': 1,
        # GetBodyVector RBDY3
        'gbv3_Coor': False,          'gbv3_Coor_freq': 1,
        'gbv3_Velo': False,          'gbv3_Velo_freq': 1,
        'gbv3_Fext': False,          'gbv3_Fext_freq': 1,
        'gbv3_Reac': False,          'gbv3_Reac_freq': 1,
        'gbv3_Acce': False,          'gbv3_Acce_freq': 1,
        'gbv3_RigidBodyMass': False, 'gbv3_RigidBodyMass_freq': 1,
        'use_restart': False, 'restart_step': 0,
        'use_stop_crit': False, 'stop_crit_type': 'energy',
        'stop_crit_val': 1e-6, 'stop_crit_freq': 10,
        'use_multi_step': False, 'multi_step_nb': 3,
        'multi_step_sizes': '1e-3, 1e-4, 1e-5',
        # Params numeriques (fournis par ComputeTab)
        'dt': 1e-3, 'nb_steps': 1000, 'theta': 0.5,
        'tol': 1.666e-4, 'relax': 1.0, 'norm': 'Quad ',
        'gs_it1': 50, 'gs_it2': 1000,
        'solver_type': 'Stored_Delassus_Loops         ',
        'freq_write': 50, 'freq_display': 50,
        'disable_log': False,
    }

    def __init__(self, controller):
        self.controller = controller

    # =========================================================================
    # API publique
    # =========================================================================

    def generate(self, output_path: Path, params: Dict[str, Any]):
        """Ecrit command.py dans output_path."""
        output_path.write_text(
            self.generate_string(params), encoding='utf-8'
        )

    def generate_string(self, params: Dict[str, Any]) -> str:
        """Retourne le script complet sous forme de chaine."""
        p   = {**self._DEFAULTS, **params}
        buf = StringIO()
        w   = buf.write

        dim        = self.controller.state.dimension
        deformable = p['deformable']
        mhyp       = p['mhyp']

        # ── Flags de commodite ────────────────────────────────────────────────
        use_RBDY2   = p['use_RBDY2']   and dim == 2
        use_RBDY3   = p['use_RBDY3']   and dim == 3
        use_mecaFEM = p['use_mecaFEM'] and deformable
        use_therFEM = p['use_therFEM'] and deformable
        use_hydrFEM = p['use_hydrFEM'] and deformable
        any_FEM     = use_mecaFEM or use_therFEM or use_hydrFEM

        tacts_2d = [t for t in (
            'DKDKx','DKJCx','DKKDx','PLPLx','CLALp','ALpALp'
        ) if p.get(f'use_{t}')]
        tacts_3d = [t for t in (
            'SPSPx','SPCDx','SPPLx','CDCDx','CDPLx','PRPRx'
        ) if p.get(f'use_{t}')]
        tacts_mix = [t for t in (
            'DKMECAx','ALpMECAx','SPMECAx'
        ) if p.get(f'use_{t}')]
        tacts_pt  = [t for t in (
            'PT2Dx','PT3Dx','NODES'
        ) if p.get(f'use_{t}')]
        all_tacts = tacts_2d + tacts_3d + tacts_mix + tacts_pt

        use_multi   = p.get('use_multi_step', False)
        use_restart = p.get('use_restart', False)
        use_stop    = p.get('use_stop_crit', False)

        # ── 1. En-tete ────────────────────────────────────────────────────────
        w('# -*- coding: utf-8 -*-\n')
        w('# Script de calcul genere automatiquement par LMGC90_GUI\n')
        w(f'# Projet    : {self.controller.state.name}\n')
        w(f'# Dimension : {dim}D\n')
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
            nb        = p.get('multi_step_nb', 3)
            w('# Multi-pas : sequence de pas de temps\n')
            w(f'dt_sequence      = [{sizes_str}]\n')
            w(f'steps_per_phase  = nb_steps // {nb}\n')
            w('\n')

        if use_stop:
            w('# Critere d\'arret\n')
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

        # ── 4b. Desactivation des logs (si demande) ──────────────────────────
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

        # ── 6b. Visibilite des avatars ────────────────────────────────────────
        def _write_vis_calls(key, func, guard):
            """Ecrit un appel chipy.func(id) pour chaque ID dans la chaine."""
            if not guard:
                return
            ids_str = p.get(key, '')
            ids = [tok.strip() for tok in ids_str.split(',') if tok.strip().isdigit()]
            for av_id in ids:
                w('chipy.{}({})\n'.format(func, av_id))

        _write_vis_calls('vis_RBDY2_visible',   'RBDY2_SetVisible',   use_RBDY2)
        _write_vis_calls('vis_RBDY2_invisible', 'RBDY2_SetInvisible', use_RBDY2)
        _write_vis_calls('vis_RBDY3_visible',   'RBDY3_SetVisible',   use_RBDY3)
        _write_vis_calls('vis_RBDY3_invisible', 'RBDY3_SetInvisible', use_RBDY3)

        _any_vis = any(
            bool([t for t in p.get(k, '').split(',') if t.strip().isdigit()])
            for k in ('vis_RBDY2_visible','vis_RBDY2_invisible',
                      'vis_RBDY3_visible','vis_RBDY3_invisible')
        )
        if _any_vis:
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
            w("    chipy.utilities_logMes("
              "f'PHASE {_phase + 1} / {len(dt_sequence)} — dt = {_dt}')\n")
            w('    for k in range(steps_per_phase):\n')
            ind = '        '
        else:
            w('# ── Boucle de calcul ─────────────────────────────────────\n')
            w('for k in range(nb_steps):\n')
            ind = '    '

        # Raccourci
        def L(line: str):
            w(ind + line + '\n')

        L("chipy.utilities_logMes('INCREMENT STEP')")
        L('chipy.IncrementStep()')
        w('\n')

        # a. FreeVelocity corps rigides
        if use_RBDY2:
            L("chipy.utilities_logMes('COMPUTE Fext/Fint — RBDY2')")
            L('chipy.ComputeFext()')
            L('chipy.ComputeBulk()')
            L("chipy.utilities_logMes('COMPUTE Free Velocity — RBDY2')")
            L('chipy.ComputeFreeVelocity()')
        if use_RBDY3:
            L("chipy.utilities_logMes('COMPUTE Free Velocity — RBDY3')")
            L('chipy.RBDY3_NewStep()')
            L('chipy.RBDY3_FreeVelocity()')
        w('\n')

        # b. FreeVelocity deformables
        if use_mecaFEM:
            L("chipy.utilities_logMes('mecaFEMx — assembly + FreeVelocity')")
            L('chipy.mecaFEMx_ComputeFext()')
            L('chipy.mecaFEMx_ComputeBulk()')
            L('chipy.mecaFEMx_ComputeFreeVelocity()')
        if use_therFEM:
            L("chipy.utilities_logMes('therFEMx — flux + FreeVelocity')")
            L('chipy.therFEMx_ComputeFext()')
            L('chipy.therFEMx_ComputeBulk()')
            L('chipy.therFEMx_ComputeFreeVelocity()')
        if use_hydrFEM:
            L("chipy.utilities_logMes('hydrFEMx — pression + FreeVelocity')")
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
            'extract_energy','extract_KE','extract_Rnod',
            'extract_Vloc','extract_Rloc',
            'extract_fields','extract_internal'
        )):
            w('\n')

        # GetBodyVector RBDY2
        _gbv2_active = [v for v in (
            'Coor0','Coor_','Coorb','Coorm','X____','V____','Vbeg_', 'Vfree', 'Fext', 'Fint_', 'Reac', 'Ireac',
        ) if p.get('gbv2_{}'.format(v))]
        if _gbv2_active and use_RBDY2:
            L("chipy.utilities_logMes('RBDY2 GetBodyVector')")
            for _v in _gbv2_active:
                _freq = p.get('gbv2_{}_freq'.format(_v), 1)
                L('if k % {} == 0:'.format(_freq))
                w(ind + '    chipy.RBDY2_GetBodyVector(\'{}\')\n'.format(_v))
            w('\n')

        # GetBodyVector RBDY3
        _gbv3_active = [v for v in (
            'Coor0','Coor_','Coorb','Coorm','X____','V____','Vbeg_', 'Vfree', 'Fext', 'Fint_', 'Reac', 'Ireac',
        ) if p.get('gbv3_{}'.format(v))]
        if _gbv3_active and use_RBDY3:
            L("chipy.utilities_logMes('RBDY3 GetBodyVector')")
            for _v in _gbv3_active:
                _freq = p.get('gbv3_{}_freq'.format(_v), 1)
                L('if k % {} == 0:'.format(_freq))
                w(ind + '    chipy.RBDY3_GetBodyVector(\'{}\')\n'.format(_v))
            w('\n')

        # h. Critere d'arret
        if use_stop:
            L('# Critere d\'arret')
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
            w(ind + "            f'Critere atteint a k={k} :"\
                    " {_crit:.4e} < {stop_tol:.2e}')\n")
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
                L('chipy.RBDY2_WriteDisplayFiles(freq_display)')
                wrote_visu = True
            if p.get('visu_RBDY3') and use_RBDY3:
                L('chipy.RBDY3_WriteDisplayFiles(freq_display)')
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
                # Fallback generique si aucune visu specifique
                L('chipy.WriteDisplayFiles(freq_display)')
            L('chipy.WritePostproFiles()')
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