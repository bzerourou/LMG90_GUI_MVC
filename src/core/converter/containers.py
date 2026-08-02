"""Conteneurs génériques (pre.avatars(), pre.materials(), etc.) et suivi des boucles."""
from typing import Any, List

from .proxies_avatar import _AvatarObj, _MeshAvatarObj, _EmptyAvatarObj

_AVATAR_TYPES = (_AvatarObj, _MeshAvatarObj, _EmptyAvatarObj)


class _Container:
    def __init__(self, kind=''):
        self._items: List[Any] = []
        self._kind = kind

    def _add(self, item): self._items.append(item)

    def addAvatar(self, item):    self._add(item)
    def addMaterial(self, *args):
        for a in args: self._add(a)
    def addModel(self, item):     self._add(item)
    def addBehav(self, item):     self._add(item)
    def addSeeTable(self, item):  self._add(item)
    def addCommand(self, item):   self._add(item)

    def __iadd__(self, item):
        self._add(item)
        return self

    def __iter__(self):   return iter(self._items)
    def __len__(self):    return len(self._items)
    def __repr__(self):   return f"Container({self._kind}, {len(self._items)} items)"


class _SilentModule:
    def __init__(self, name):     self._name = name
    def __getattr__(self, k):     return _SilentModule(f"{self._name}.{k}")
    def __call__(self, *a, **kw): return _SilentModule(f"{self._name}()")
    def __iadd__(self, o):        return self
    def show(self, *a, **kw):     pass
    def savefig(self, *a, **kw):  pass


class _TrackedContainer(_Container):
    """
    Conteneur bodies enrichi : tague chaque avatar avec son indice de boucle
    et met a jour les masonry_patterns.
    """

    def __init__(self, converter):
        super().__init__('bodies')
        self._cv = converter

    def _register(self, item) -> None:
        if not isinstance(item, _AVATAR_TYPES):
            return
        body_idx = len(self._items)
        self._items.append(item)

        active = self._cv._active_loop_idx
        if active is not None:
            item._loop_idx = active
            self._cv._loop_captures[active]['avatar_indices'].append(body_idx)

        masonry_idx = getattr(item, '_masonry_idx', None)
        if (masonry_idx is not None
                and masonry_idx < len(self._cv._masonry_patterns)):
            self._cv._masonry_patterns[masonry_idx]['avatar_indices'].append(body_idx)

    def addAvatar(self, item):
        if isinstance(item, list):
            for av in item:
                self._register(av)
        elif isinstance(item, _AVATAR_TYPES):
            self._register(item)

    def __iadd__(self, item):
        self.addAvatar(item)
        return self