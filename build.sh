#!/bin/bash
# ================================================================
# build.sh - Génère l'exécutable LMGC90_GUI pour Linux
# À la racine du projet, à côté de main.py et rthook_qt6.py
# ================================================================

set -e  # Exit on error

# Nettoyage des répertoires précédents
echo "Nettoyage des répertoires de build précédents..."
rm -rf build dist

# Build avec PyInstaller
echo "Compilation de LMGC90_GUI pour Linux..."
pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --clean \
    --name="LMGC90_GUI" \
    --icon=ico.png \
    --collect-all pylmgc90 \
    --collect-all pyvistaqt \
    --collect-all PyQt6 \
    --collect-all gmsh \
    --collect-all vtkmodules \
    --collect-all vtk \
    --hidden-import=vtkmodules.all \
    --hidden-import=vtkmodules.util.execution_model \
    --hidden-import=vtkmodules.util.numpy_support \
    --hidden-import=vtkmodules.util.vtkAlgorithm \
    --hidden-import=vtkmodules.util.vtkVariant \
    --hidden-import=vtkmodules.vtkRenderingOpenGL2 \
    --hidden-import=vtkmodules.vtkInteractionStyle \
    --hidden-import=vtkmodules.vtkIOXML \
    --hidden-import=vtkmodules.vtkIOLegacy \
    --hidden-import=vtkmodules.vtkIOGeometry \
    --hidden-import=vtkmodules.vtkCommonCore \
    --hidden-import=vtkmodules.vtkCommonDataModel \
    --hidden-import=vtkmodules.vtkFiltersCore \
    --runtime-hook=rthook_qt6.py \
    main.py

# Rendre l'exécutable exécutable
chmod +x dist/LMGC90_GUI/LMGC90_GUI

echo ""
echo "================================================================"
echo "Build terminé : dist/LMGC90_GUI/LMGC90_GUI"
echo "================================================================"
echo ""
echo "Pour lancer l'application :"
echo "  ./dist/LMGC90_GUI/LMGC90_GUI"
