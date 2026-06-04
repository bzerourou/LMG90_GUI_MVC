# 🔨 Guide de Compilation LMGC90_GUI - Multi-Plateforme

Ce guide explique comment générer des exécutables LMGC90_GUI pour Windows, Linux et macOS.

## 📋 Prérequis

Assurez-vous que vous avez PyInstaller installé dans votre environnement conda :

```bash
pip install pyinstaller
```

Vérifiez aussi que vous avez tous les fichiers nécessaires à la racine du projet :
- `main.py` - Point d'entrée de l'application
- `rthook_qt6.py` - Hook d'exécution pour Qt6
- `ico.png` - Icône de l'application

## 🚀 Méthode 1 : Script Python Universel (Recommandé)

Le script `build_all.py` détecte automatiquement votre système d'exploitation et configure le build correctement.

### Sur Windows :
```bash
python build_all.py
```

### Sur Linux :
```bash
python build_all.py
# ou
python3 build_all.py
```

### Sur macOS :
```bash
python3 build_all.py
```

### Options disponibles :
```bash
python build_all.py --clean    # Nettoie uniquement les répertoires de build
python build_all.py --help     # Affiche l'aide
```

## 🔧 Méthode 2 : Scripts Natifs (Alternative)

### Windows
```bash
.\build.bat
```

Le résultat sera dans `dist\LMGC90_GUI\LMGC90_GUI.exe`

### Linux
```bash
chmod +x build.sh
./build.sh
```

Le résultat sera dans `dist/LMGC90_GUI/LMGC90_GUI`

### macOS
```bash
chmod +x build-mac.sh
./build-mac.sh
```

Le résultat sera dans `dist/LMGC90_GUI/LMGC90_GUI`

## 📂 Structure des Fichiers Générés

Après la compilation, vous aurez une structure `dist/` contenant :

### Windows
```
dist/
└── LMGC90_GUI/
    ├── LMGC90_GUI.exe (exécutable principal)
    ├── python311.dll (et autres DLLs)
    ├── PyQt6/ (bibliothèques Qt)
    ├── vtkmodules/ (VTK)
    └── ... (autres dépendances)
```

### Linux
```
dist/
└── LMGC90_GUI/
    ├── LMGC90_GUI (exécutable principal)
    ├── _internal/ (dépendances)
    └── ... (autres fichiers)
```

### macOS
```
dist/
└── LMGC90_GUI/
    ├── LMGC90_GUI (exécutable principal)
    ├── _internal/ (dépendances)
    └── ... (autres fichiers)
```

## 🎯 Lancer l'Application

### Windows
- Double-cliquer sur `dist\LMGC90_GUI\LMGC90_GUI.exe`
- Ou depuis terminal : `.\dist\LMGC90_GUI\LMGC90_GUI.exe`

### Linux
```bash
./dist/LMGC90_GUI/LMGC90_GUI
```

Pour créer un lanceur de bureau :
```bash
# Créer un fichier .desktop dans ~/.local/share/applications/
[Desktop Entry]
Type=Application
Name=LMGC90 GUI
Exec=/chemin/complet/vers/dist/LMGC90_GUI/LMGC90_GUI
Icon=lmgc90
Terminal=false
```

### macOS
```bash
./dist/LMGC90_GUI/LMGC90_GUI
```

Ou depuis le Finder, localiser et double-cliquer sur `LMGC90_GUI` dans `dist/LMGC90_GUI/`

## 🔧 Configuration Avancée

### Icônes Personnalisées

**Pour Windows :**
- Format requis : `.ico` ou `.png`
- Taille recommandée : 256x256 pixels ou plus

**Pour macOS :**
- Format requis : `.icns` (format natif macOS)
- Convertir une image PNG en ICNS :
  ```bash
  # Utiliser un outil en ligne ou Image2Icon
  sips -z 1024 1024 ico.png --out temp.png
  # Puis convertir avec un outil approprié
  ```

**Pour Linux :**
- Format requis : `.png`
- Taille recommandée : 256x256 pixels ou plus

### Signature de Code (macOS)

Pour signer l'application :
```bash
codesign -s - --deep --force dist/LMGC90_GUI/LMGC90_GUI
```

Pour signer avec un certificat de développeur :
```bash
codesign -s "Developer ID Application" --deep dist/LMGC90_GUI/LMGC90_GUI
```

### Créer un DMG (macOS)

Si vous avez `create-dmg` installé :
```bash
brew install create-dmg
create-dmg \
    --volname "LMGC90 GUI" \
    --window-size 600 400 \
    --icon-size 100 \
    dist/LMGC90_GUI.dmg \
    dist/LMGC90_GUI
```

## 🐛 Dépannage

### PyInstaller non trouvé
```bash
pip install pyinstaller
```

### Erreur de dépendances manquantes
Assurez-vous que tous les modules requis sont installés :
```bash
pip install -r requirements.txt
```

### L'application ne démarre pas
1. Vérifiez les logs : `build/warn-LMGC90_GUI.txt`
2. Essayez de lancer depuis le terminal pour voir les erreurs
3. Vérifiez que `rthook_qt6.py` existe et est valide

### Problèmes de Qt6 sur Linux
Si Qt6 ne fonctionne pas, installez les dépendances :
```bash
# Debian/Ubuntu
sudo apt-get install libqt6gui6 libqt6core6

# Fedora/RHEL
sudo dnf install qt6-qtbase
```

### L'application est trop volumineuse
Le répertoire `dist/` peut être important (100-500 MB) car il contient toutes les dépendances bundlées. C'est normal et nécessaire pour que l'application soit autonome.

Pour réduire la taille :
1. Exclure les modules non utilisés avec `--exclude-module`
2. Utiliser UPX pour compresser les binaires (déjà activé par défaut)

## 📦 Distribution

### Windows
- Créer un installateur avec NSIS : [nsis.sourceforge.io](https://nsis.sourceforge.io/)
- Ou distribuer le répertoire `dist/LMGC90_GUI/` complet

### Linux
- Créer un package AppImage : [appimage.org](https://appimage.org/)
- Ou créer un package `.deb` ou `.rpm`
- Ou distribuer le répertoire `dist/LMGC90_GUI/` complet

### macOS
- Créer un fichier DMG (voir section "Créer un DMG")
- Ou distribuer le répertoire `dist/LMGC90_GUI/` complet
- Pour la distribution sur l'App Store, notariser d'abord : [developer.apple.com](https://developer.apple.com/)

## 🔄 Intégration Continue (CI/CD)

Pour automatiser les builds sur tous les OS avec GitHub Actions, voir le fichier `.github/workflows/build.yml`.

## 📝 Notes Importantes

1. **Dépendances VTK/PyVista** : Ces bibliothèques incluent des composants compilés volumineux. La taille du build est normale.

2. **Performance** : Le premier lancement peut être plus lent car Python doit initialiser toutes les dépendances bundlées.

3. **Antivirus** : Les exécutables générés peuvent être flaggés par certains antivirus comme "inconnu". C'est normal pour les exécutables auto-compilés. La signature de code (notamment pour macOS) peut aider.

4. **Mise à Jour** : Pour créer des mises à jour, il suffit de recompiler avec la nouvelle version du code. Il n'y a pas de système de mise à jour automatique.

## 📞 Support

Pour des problèmes spécifiques :
1. Consultez les logs dans `build/warn-LMGC90_GUI.txt`
2. Vérifiez la documentation PyInstaller : [pyinstaller.org](https://pyinstaller.org/)
3. Vérifiez les dépendances : PyQt6, PyVista, VTK, etc.
