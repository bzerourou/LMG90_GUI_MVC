"""Routage des sélections de l'arbre vers les onglets d'édition."""
from ...core.models import AvatarOrigin, AvatarType


class MainWindowTreeMixin:
    """Connecte les éléments sélectionnés aux vues correspondantes."""

    # item_type arbre → (tab_id, getter OU attribut state, passer l'index)
    # Pour DOF / postpro on lit state.operations / state.postpro_commands
    # (pas les getters, qui lèvent IndexError hors bornes).
    _TREE_EDIT_ROUTES = {
        "material":      ("material",   "get_material",        None,                  False),
        "model":         ("model",      "get_model",           None,                  False),
        "loop":          ("loop",       "get_loop",            None,                  True),
        "contact_law":   ("contact",    "get_contact_law",     None,                  False),
        "visibility":    ("visibility", "get_visibility_rule", None,                  True),
        "dof_operation": ("dof",        None,                  "operations",          True),
        "postpro":       ("postpro",    None,                  "postpro_commands",    False),
    }

    def _on_tree_item_selected(self, item_type: str, item_data):
        """Ouvre l'onglet correspondant et charge l'élément en édition.

        Les dépôts granulo et les avatars générés par granulométrie
        ne passent pas en mode édition.
        """
        if item_type == "granulo":
            self.statusBar().showMessage(
                "Dépôt granulo : pas d'édition individuelle "
                "(régénérer via Granulométrie).",
                4000,
            )
            return

        if item_type == "avatar":
            self._open_avatar_for_edit(item_data)
            return

        route = self._TREE_EDIT_ROUTES.get(item_type)
        if route is None:
            return

        tab_id, getter_name, state_attr, pass_index = route
        element = self._resolve_tree_element(getter_name, state_attr, item_data)
        if element is None:
            return

        self._add_tab(tab_id)
        tab = self.all_tabs[tab_id][1]
        loader = getattr(tab, "load_for_edit", None)
        if loader is None:
            return
        if pass_index:
            loader(item_data, element)
        else:
            loader(element)

    def _resolve_tree_element(self, getter_name, state_attr, item_data):
        """Récupère l'objet métier sans lever d'exception hors bornes."""
        if state_attr:
            collection = getattr(self.controller.state, state_attr, None) or []
            try:
                index = int(item_data)
            except (TypeError, ValueError):
                return None
            if 0 <= index < len(collection):
                return collection[index]
            return None

        getter = getattr(self.controller, getter_name, None)
        if getter is None:
            return None
        try:
            return getter(item_data)
        except (IndexError, KeyError, TypeError):
            return None

    def _open_avatar_for_edit(self, index: int) -> None:
        avatar = self.controller.get_avatar(index)
        if not avatar:
            return

        if avatar.origin == AvatarOrigin.GRANULO:
            self.statusBar().showMessage(
                "Avatar généré par granulométrie : pas d'édition individuelle.",
                4000,
            )
            return

        is_masonry = (
            avatar.avatar_type == AvatarType.EMPTY_AVATAR
            and avatar.wall_params
            and "l" in avatar.wall_params
            and "h" in avatar.wall_params
        )
        use_empty = (
            avatar.avatar_type == AvatarType.EMPTY_AVATAR and not is_masonry
        )
        tab_id = "empty_avatar" if use_empty else "avatar"
        self._add_tab(tab_id)
        tab = self.empty_avatar_tab if use_empty else self.avatar_tab
        tab.load_for_edit(index, avatar)