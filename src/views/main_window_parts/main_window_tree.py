"""Routage des sélections de l'arbre vers les onglets d'édition."""
from ...core.models import AvatarOrigin, AvatarType


class MainWindowTreeMixin:
    """Connecte les éléments sélectionnés aux vues correspondantes."""

    # item_type arbre → (tab_id, getter, passer l'index à load_for_edit)
    _TREE_EDIT_ROUTES = {
        "material":       ("material",   "get_material",         False),
        "model":          ("model",      "get_model",            False),
        "loop":           ("loop",       "get_loop",             True),
        "contact_law":    ("contact",    "get_contact_law",      False),
        "visibility":     ("visibility", "get_visibility_rule",  True),
        "dof_operation":  ("dof",        "get_dof_operation",    True),
        "postpro":        ("postpro",    "get_postpro_command",  False),
    }

    def _on_tree_item_selected(self, item_type: str, item_data):
        """Ouvre l'onglet correspondant et charge l'élément en édition.

        Les dépôts granulo et les avatars générés par granulométrie
        ne passent pas en mode édition (régénérer via l'onglet / l'assistant).
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

        tab_id, getter_name, pass_index = route
        element = getattr(self.controller, getter_name)(item_data)
        if not element:
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