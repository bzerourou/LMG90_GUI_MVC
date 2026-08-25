"""Composants extraits de la fenetre principale."""

from .command_palette_controller import CommandPaletteController
from .main_window_layout import MainWindowLayoutMixin
from .main_window_tabs import MainWindowTabsMixin
from .main_window_tree import MainWindowTreeMixin

__all__ = [
    "CommandPaletteController",
    "MainWindowLayoutMixin",
    "MainWindowTabsMixin",
    "MainWindowTreeMixin",
]
