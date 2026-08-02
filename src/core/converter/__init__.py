"""
convert — Convertisseur script pylmgc90 -> projet .lmgc90 (GUI)

Package scindé (ancien fichier monolithique convert.py) pour faciliter la
maintenance. L'API publique reste inchangée pour tous les appelants
existants (convert_dialog.py, CLI) :

    from ...core.convert import Converter, convert

Répartition :
  proxies_avatar.py   — corps rigides créés directement (_AvatarObj),
                         avatar vide (_EmptyAvatarObj), maillages (_MeshAvatarObj)
  proxies_data.py      — matériaux, modèles, lois de contact, visibilité,
                         postpro, granulométrie
  proxies_masonry.py   — briques et murs (pre.brick2D/3D, paneresse_simple/double)
  proxies_runtime.py   — range()/np.linspace() trackés pour capter les boucles
  containers.py        — conteneurs génériques (pre.avatars(), bodies trackés)
  mock_pre.py           — _MockPre, le module fantôme remplaçant pylmgc90.pre
  ast_analyzer.py       — analyse statique du script (variables, boucles for)
  utils.py              — fonctions utilitaires de sérialisation
  converter.py          — Converter, orchestrateur principal
  cli.py                — interface ligne de commande
"""
from .converter import Converter
from .cli import convert, main

__all__ = ["Converter", "convert", "main"]