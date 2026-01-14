
from pathlib import Path

class ComputeScriptGenerator:
    """Génère le script command.py"""
    
    def __init__(self, controller):
        self.controller = controller
    
    def generate(self, output_path: Path, params: dict):
        """Génère le script"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("""# -*- coding: utf-8 -*-
# Script de calcul généré automatiquement par LMGC90_GUI

from pylmgc90 import chipy

# Initialisation
chipy.Initialize()
chipy.checkDirectories()

# Paramètres
dim = """ + str(self.controller.state.dimension) + """
mhyp = 1

dt = """ + str(params['dt']) + """
nb_steps = """ + str(params['nb_steps']) + """
theta = """ + str(params['theta']) + """

Rloc_tol = 5.e-2

tol = """ + str(params['tol']) + """
relax = """ + str(params['relax']) + """
norm = '""" + params['norm'] + """'
gs_it1 = """ + str(params['gs_it1']) + """
gs_it2 = """ + str(params['gs_it2']) + """
solver_type = '""" + params['solver_type'] + """'

freq_write = """ + str(params['freq_write']) + """
freq_display = """ + str(params['freq_display']) + """
ref_radius = 5.e-2

# Configuration
chipy.SetDimension(dim, mhyp)
chipy.utilities_logMes('INIT TIME STEPPING')
chipy.TimeEvolution_SetTimeStep(dt)
chipy.Integrator_InitTheta(theta)

chipy.ReadDatbox(deformable=False)

chipy.utilities_logMes('DISPLAY & WRITE')
chipy.OpenDisplayFiles()
chipy.OpenPostproFiles()

# Boucle de calcul
chipy.utilities_logMes('COMPUTE MASS')
chipy.ComputeMass()

for k in range(0, nb_steps):
    chipy.utilities_logMes('INCREMENT STEP')
    chipy.IncrementStep()
    
    chipy.utilities_logMes('COMPUTE Fext')
    chipy.ComputeFext()
    chipy.utilities_logMes('COMPUTE Fint')
    chipy.ComputeBulk()
    chipy.utilities_logMes('COMPUTE Free Vlocy')
    chipy.ComputeFreeVelocity()
    
    chipy.utilities_logMes('SELECT PROX TACTORS')
    chipy.SelectProxTactors()
    
    chipy.utilities_logMes('RESOLUTION')
    chipy.RecupRloc(Rloc_tol)
    
    chipy.ExSolver(solver_type, norm, tol, relax, gs_it1, gs_it2)
    chipy.UpdateTactBehav()
    
    chipy.StockRloc()
    
    chipy.utilities_logMes('COMPUTE DOF, FIELDS, etc.')
    chipy.ComputeDof()
    
    chipy.utilities_logMes('UPDATE DOF, FIELDS')
    chipy.UpdateStep()
    
    chipy.utilities_logMes('WRITE OUT')
    chipy.WriteOut(freq_write)
    
    chipy.utilities_logMes('VISU & POSTPRO')
    chipy.WriteDisplayFiles(freq_display)
    chipy.WritePostproFiles()

# Fin
chipy.CloseDisplayFiles()
chipy.ClosePostproFiles()
chipy.Finalize()

print("✅ CALCUL TERMINÉ")
""")