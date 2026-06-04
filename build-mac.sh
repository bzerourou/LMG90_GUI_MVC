#!/bin/bash
# ================================================================
# build-mac.sh - Génère l'exécutable LMGC90_GUI pour macOS
# À la racine du projet, à côté de main.py et rthook_qt6.py
# ================================================================

set -e  # Exit on error

# Nettoyage des répertoires précédents
echo "Nettoyage des répertoires de build précédents..."
rm -rf build dist

# Créer un fichier icns si ico.png existe
if [ -f "ico.png" ]; then
    echo "Conversion de ico.png en format macOS icns..."
    # Conversion simple - pour une meilleure qualité, utiliser Image2Icon ou similaire
    sips -z 1024 1024 ico.png --out ico_1024.png 2>/dev/null || true
fi

# Build avec PyInstaller pour macOS
echo "Compilation de LMGC90_GUI pour macOS..."
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
    --osx-bundle-identifier="com.lmgc90.gui" \
    main.py

# Rendre l'exécutable exécutable
chmod +x dist/LMGC90_GUI/LMGC90_GUI

# Créer un DMG (optionnel)
# Vous pouvez installer create-dmg : brew install create-dmg
# Puis décommenter les lignes ci-dessous

# if command -v create-dmg &> /dev/null; then
#     echo "Création du fichier DMG..."
#     create-dmg \
#         --volname "LMGC90 GUI" \
#         --volicon ico.png \
#         --window-pos 200 120 \
#         --window-size 600 400 \
#         --icon-size 100 \
#         --icon "LMGC90_GUI" 175 190 \
#         --hide-extension "LMGC90_GUI" \
#         --app-drop-link 425 190 \
#         dist/LMGC90_GUI.dmg \
#         dist/LMGC90_GUI
# fi

echo ""
echo "================================================================"
echo "Build terminé : dist/LMGC90_GUI/LMGC90_GUI"
echo "================================================================"
echo ""
echo "Pour lancer l'application :"
echo "  ./dist/LMGC90_GUI/LMGC90_GUI"
echo ""
echo "Ou en double-cliquant sur l'application depuis le Finder."
