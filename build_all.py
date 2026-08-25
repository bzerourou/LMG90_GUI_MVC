#!/usr/bin/env python3
# ================================================================
# build_all.py - Script de build universel pour tous les OS
# Compile LMGC90_GUI pour Windows, Linux et macOS
# ================================================================

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


class BuildManager:
    """Gestionnaire de build cross-plateforme"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.system = platform.system()
        self.machine = platform.machine()
        
    def clean_build_dirs(self):
        """Nettoie les repertoires de build precedents"""
        print("?? Nettoyage des repertoires de build precedents...")
        for dir_name in ["build", "dist"]:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   ? Suppression de {dir_name}/")
    
    def run_pyinstaller(self, icon_path="ico.png"):
        """Execute PyInstaller avec la configuration commune"""
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--windowed",
            "--clean",
            "--noupx",
            "--name=LMGC90_GUI",
            f"--icon={icon_path}",
            "--collect-all=pylmgc90",
            "--collect-all=numpy",
            "--collect-all=pyvistaqt",
            "--collect-all=PyQt6",
            "--collect-all=gmsh",
            "--collect-all=vtkmodules",
            "--collect-all=vtk",
            "--hidden_import=pylmgc90",
            "--hidden_import=pylmgc90.pre",
            "--hidden-import=vtkmodules.all",
            "--hidden-import=vtkmodules.util.execution_model",
            "--hidden-import=vtkmodules.util.numpy_support",
            "--hidden-import=vtkmodules.util.vtkAlgorithm",
            "--hidden-import=vtkmodules.util.vtkVariant",
            "--hidden-import=vtkmodules.vtkRenderingOpenGL2",
            "--hidden-import=vtkmodules.vtkInteractionStyle",
            "--hidden-import=vtkmodules.vtkIOXML",
            "--hidden-import=vtkmodules.vtkIOLegacy",
            "--hidden-import=vtkmodules.vtkIOGeometry",
            "--hidden-import=vtkmodules.vtkCommonCore",
            "--hidden-import=vtkmodules.vtkCommonDataModel",
            "--hidden-import=vtkmodules.vtkFiltersCore",
            "--runtime-hook=rthook_qt6.py",
            "main.py"
        ]
        
        if self.system == "Darwin":  # macOS
            cmd.append("--osx-bundle-identifier=com.lmgc90.gui")
        
        print(f"?? Compilation de LMGC90_GUI pour {self.system}...")
        result = subprocess.run(cmd, cwd=self.project_root, check=False)
        
        if result.returncode != 0:
            print(f"? Erreur lors de la compilation PyInstaller")
            return False
        
        # Rendre l'ex�cutable ex�cutable sur Unix
        if self.system in ["Linux", "Darwin"]:
            exe_path = self.project_root / "dist" / "LMGC90_GUI" / "LMGC90_GUI"
            if exe_path.exists():
                os.chmod(exe_path, 0o755)
                print(f"? Permissions definies pour l'executable")
        
        return True
    
    def create_app_bundle_macos(self):
        """Cree un bundle d'application macOS propre"""
        if self.system != "Darwin":
            return
        
        print("?? Creation du bundle d'application macOS...")
        dist_path = self.project_root / "dist" / "LMGC90_GUI"
        app_path = self.project_root / "dist" / "LMGC90_GUI.app"
        
        if app_path.exists():
            shutil.rmtree(app_path)
        
        # Cr�er la structure du bundle
        (app_path / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
        (app_path / "Contents" / "Resources").mkdir(parents=True, exist_ok=True)
        
        # Copier le contenu
        shutil.copytree(dist_path, app_path / "Contents" / "Resources" / "app")
        
        # Cr�er l'executable wrapper
        exe_wrapper = app_path / "Contents" / "MacOS" / "LMGC90_GUI"
        with open(exe_wrapper, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n")
            f.write("\"$DIR/../Resources/app/LMGC90_GUI\" \"$@\"\n")
        os.chmod(exe_wrapper, 0o755)
        
        print("? Bundle d'application cree")
    
    def print_summary(self):
        """Affiche le resume de la compilation"""
        print("\n" + "="*70)
        print("? BUILD TERMINE AVEC SUCCES")
        print("="*70)
        
        dist_path = self.project_root / "dist" / "LMGC90_GUI"
        exe_name = "LMGC90_GUI.exe" if self.system == "Windows" else "LMGC90_GUI"
        exe_path = dist_path / exe_name
        
        if exe_path.exists():
            print(f"\n?? Localisation : dist/LMGC90_GUI/{exe_name}")
            file_size = exe_path.stat().st_size / (1024*1024)  # MB
            print(f"?? Taille : {file_size:.1f} MB")
        
        print("\n?? Pour lancer l'application :")
        if self.system == "Windows":
            print(f"   dist\\LMGC90_GUI\\LMGC90_GUI.exe")
        elif self.system == "Darwin":
            print(f"   ./dist/LMGC90_GUI/LMGC90_GUI")
            print(f"   ou double-cliquer sur l'application dans Finder")
        else:  # Linux
            print(f"   ./dist/LMGC90_GUI/LMGC90_GUI")
        
        print("\n" + "="*70)
    
    def build(self):
        """Lance le processus de build complet"""
        print(f"\n{'='*70}")
        print(f"?? Demarrage du build pour {self.system} ({self.machine})")
        print(f"{'='*70}\n")
        
        # V�rifier que les fichiers requis existent
        required_files = ["main.py", "rthook_qt6.py"]
        for file in required_files:
            if not (self.project_root / file).exists():
                print(f"? Erreur : {file} non trouve dans {self.project_root}")
                return False
        
        # Ex�cuter les �tapes de build
        self.clean_build_dirs()
        
        if not self.run_pyinstaller():
            return False
        
        if self.system == "Darwin":
            self.create_app_bundle_macos()
        
        self.print_summary()
        return True


def main():
    """Fonction principale"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clean":
            manager = BuildManager()
            manager.clean_build_dirs()
            print("? Nettoyage effectue")
            return
        elif sys.argv[1] == "--help":
            print("""Usage: python build_all.py [OPTIONS]
    
Options:
    --clean     Nettoie uniquement les repertoires de build
    --help      Affiche cette aide
    
Sans options, lance la compilation complete pour le systeme d'exploitation courant.
""")
            return
    
    manager = BuildManager()
    success = manager.build()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()