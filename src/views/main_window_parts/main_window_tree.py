"""Routage des selections de l'arbre vers les onglets d'edition."""


class MainWindowTreeMixin:
    """Connecte les elements selectionnes aux vues correspondantes."""

    def _on_tree_item_selected(self, item_type: str, item_data):
        """Charge l'element selectionne dans l'onglet approprie."""
        routes = {
            "material": ("material_tab", "get_material", "load_for_edit", False),
            "model": ("model_tab", "get_model", "load_for_edit", False),
            "loop": ("loop_tab", "get_loop", "load_for_edit", True),
            "contact_law": ("contact_tab", "get_contact_law", "load_for_edit", False),
            "visibility": ("visibility_tab", "get_visibility_rule", "load_for_edit", True),
            "dof_operation": ("dof_tab", "get_dof_operation", "load_for_edit", True),
            "granulo": ("granulo_tab", "get_granulo", "load_for_edit", True),
            "postpro": ("postpro_tab", "get_postpro_command", "load_for_edit", False),
        }

        if item_type == "avatar":
            avatar = self.controller.get_avatar(item_data)
            if not avatar:
                return
            from ...core.models import AvatarType
            tab = self.empty_avatar_tab if avatar.avatar_type == AvatarType.EMPTY_AVATAR else self.avatar_tab
            self.tabs.setCurrentWidget(tab)
            if tab is self.empty_avatar_tab:
                tab.load_for_edit(item_data, avatar)
            else:
                tab.load_for_edit(item_data, avatar)
            return

        route = routes.get(item_type)
        if route is None:
            return

        tab_name, getter_name, loader_name, pass_index = route
        element = getattr(self.controller, getter_name)(item_data)
        if not element:
            return

        tab = getattr(self, tab_name)
        self.tabs.setCurrentWidget(tab)
        loader = getattr(tab, loader_name)
        if pass_index:
            loader(item_data, element)
        else:
            loader(element)
