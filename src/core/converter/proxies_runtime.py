"""Proxies range()/np.linspace() qui capturent l'imbrication des boucles for."""
import numpy as np


class _TrackedRange:
    def __init__(self, converter, r: range):
        self._cv = converter
        self._r  = r

    def __iter__(self):
        loop_idx = self._cv._push_loop(len(self._r))
        try:
            for val in self._r:
                yield val
        finally:
            self._cv._pop_loop(loop_idx)

    def __len__(self):              return len(self._r)
    def __getitem__(self, idx):     return self._r[idx]
    def __bool__(self):             return bool(self._r)
    def __contains__(self, item):   return item in self._r


class _RangeProxy:
    def __init__(self, converter):
        self._cv = converter

    def __call__(self, *args):
        return _TrackedRange(self._cv, range(*args))

    def __getattr__(self, name):
        return getattr(range, name)


class _TrackedLinspace:
    def __init__(self, converter, arr):
        self._cv  = converter
        self._arr = arr

    def __iter__(self):
        loop_idx = self._cv._push_loop(len(self._arr))
        try:
            for val in self._arr:
                yield val
        finally:
            self._cv._pop_loop(loop_idx)

    def __len__(self):              return len(self._arr)
    def __getitem__(self, idx):     return self._arr[idx]
    def __array__(self, *a, **kw):  return np.asarray(self._arr)

    def __getattr__(self, name):
        return getattr(self._arr, name)


class _NpProxy:
    def __init__(self, converter):
        self._cv = converter

    def linspace(self, start, stop, num=50, *args, **kw):
        arr = np.linspace(start, stop, int(num), *args, **kw)
        return _TrackedLinspace(self._cv, arr)

    def __getattr__(self, name):
        return getattr(np, name)