import copy

from database import (
    JsonResourceStore,
    ProfileRecoveryRequired,
    UserStore,
)


_DEFAULT_USER_STORE = None


def default_user_store(users_path):
    global _DEFAULT_USER_STORE
    if _DEFAULT_USER_STORE is None:
        _DEFAULT_USER_STORE = UserStore(seed_path=users_path)
    return _DEFAULT_USER_STORE


class UserProfileManager:
    def __init__(
        self,
        username,
        users_path="static/users.json",
        template_path="static/user_template.json",
        store=None,
        resource_store=None,
        precommit_guard=None,
    ):
        self.username = username
        self.users_path = users_path
        self.template_path = template_path
        self._locked_keys = {"username", "salt", "password"}
        self._dynamic_profile_keys = {
            "googleplex_products", "product_purchases", "storage_upgrades",
            "ghostnetwork_stats", "ghostnetwork_reward_history",
        }
        self._nullable_profile_key_types = {
            "current_city": str,
        }
        self.store = store or default_user_store(users_path)
        self.resource_store = resource_store or JsonResourceStore()
        self.precommit_guard = precommit_guard
        self._find_user_profile()
        self._sync_with_template()

    def _load_template(self, template_path=None):
        path = template_path or self.template_path
        if path == self.template_path:
            return self.resource_store.get("user_template", default={})
        return self.resource_store.get("user_template", seed_path=path, default={})

    def _sync_with_template(self, template_path=None):
        template = self._load_template(template_path)
        updated = self._recursive_sync(self.user_profile, template)
        if updated:
            self._save_changes(source="profile_manager.template_sync")

    def _recursive_sync(self, user_data: dict, template_data: dict, path=()) -> bool:
        updated = False

        for key, template_value in template_data.items():
            if key not in user_data:
                user_data[key] = copy.deepcopy(template_value)
                updated = True
            elif isinstance(template_value, dict) and isinstance(user_data[key], dict):
                updated = self._recursive_sync(user_data[key], template_value, path + (key,)) or updated

        # Template synchronization is additive-only. Runtime extensions and
        # newer fields must survive an older template; explicit cleanup belongs
        # to a versioned migration with its own receipt/guard.
        return updated

    def _load_all_users(self):
        self.all_users = self.store.list_profiles()

    def _find_user_profile(self):
        record = self.store.get_profile_with_revision(self.username)
        if not record:
            raise ValueError(f"User '{self.username}' not found.")
        if record.get("state") != "valid":
            raise ProfileRecoveryRequired(
                f"User '{self.username}' requires profile recovery."
            )

        self.user_profile = record["profile"]
        self.profile_revision = int(record["profile_revision"])
        self.original_profile = copy.deepcopy(self.user_profile)

    def add_new_user(self, new_username: str, password: str, template_path="static/user_template.json", overwrite=False):
        existing_user = self.store.get_profile(new_username)

        if existing_user and not overwrite:
            raise ValueError(f"Użytkownik '{new_username}' już istnieje.")

        template = copy.deepcopy(self._load_template(template_path))
        template["username"] = new_username
        template["password"] = password
        template["salt"] = "generated_salt_here"

        self.store.save_profile_guarded(
            template,
            expected_revision=0,
            source="profile_manager.registration",
            allow_create=True,
        )
        self._load_all_users()
        return True

    def reload_profile(self):
        self._find_user_profile()

    def update_profile(self, updates: dict):
        launch_queue_write_mode = None
        if isinstance(updates, dict) and "launch_queue" in updates:
            incoming_queue = updates.get("launch_queue")
            launch_queue_write_mode = "clear" if isinstance(incoming_queue, list) and not incoming_queue else "append"

        for key, new_value in updates.items():
            if key in self._locked_keys:
                continue

            if key in self.user_profile:
                original_value = self.user_profile[key]
                original_type = type(original_value)
                nullable_type = self._nullable_profile_key_types.get(key)
                if nullable_type and (new_value is None or isinstance(new_value, nullable_type)):
                    self.user_profile[key] = new_value
                elif isinstance(new_value, original_type):
                    self.user_profile[key] = new_value
                else:
                    raise TypeError(f"Typ wartości dla '{key}' musi być {original_type.__name__}.")
            else:
                self.user_profile[key] = new_value

        if launch_queue_write_mode:
            self.user_profile["_launch_queue_write_mode"] = launch_queue_write_mode
        self._save_changes(source="profile_manager.update_profile")

    def update_profile_value(self, profile_key: str, new_value):
        if profile_key in self._locked_keys:
            raise PermissionError(f"Nie można edytować klucza chronionego: {profile_key}")

        if profile_key not in self.user_profile:
            raise KeyError(f"Klucz '{profile_key}' nie istnieje w profilu użytkownika.")

        current_value = self.user_profile[profile_key]
        current_type = type(current_value)
        nullable_type = self._nullable_profile_key_types.get(profile_key)

        if nullable_type and (new_value is None or isinstance(new_value, nullable_type)):
            self.user_profile[profile_key] = new_value

        elif isinstance(current_value, list):
            if not isinstance(new_value, list):
                new_value = [new_value]
            for item in new_value:
                if item not in current_value:
                    current_value.append(item)

        elif isinstance(current_value, dict):
            if not isinstance(new_value, dict):
                raise TypeError(f"Nowa wartość dla '{profile_key}' musi być słownikiem.")
            current_value.update(new_value)

        elif isinstance(current_value, (str, int, float, bool)):
            if isinstance(new_value, current_type):
                self.user_profile[profile_key] = new_value
            else:
                raise TypeError(f"Typ wartości dla '{profile_key}' musi być {current_type.__name__}.")

        else:
            raise TypeError(f"Typ danych '{current_type}' nieobsługiwany dla aktualizacji.")

        self._save_changes(source="profile_manager.update_profile_value")

    def update_hacked_target_by_coords(self, lat, lng, update_data: dict) -> bool:
        hacked_list = self.user_profile.get("hacked", [])
        for i, target in enumerate(hacked_list):
            target_lng = target.get("lng", target.get("lon", 0))
            if round(target.get("lat", 0), 5) == round(lat, 5) and round(target_lng, 5) == round(lng, 5):
                for k, v in update_data.items():
                    if isinstance(target.get(k), dict) and isinstance(v, dict):
                        target[k].update(v)
                    else:
                        target[k] = v
                self.user_profile["hacked"][i] = target
                self._save_changes(source="profile_manager.update_hacked_target")
                return True
        return False

    def remove_from_list_by_coords(self, key_of_list, lat, lng, label=None) -> bool:
        if not isinstance(self.user_profile.get(key_of_list), list):
            return False

        targets = self.user_profile.get(key_of_list, [])
        for i, target in enumerate(targets):
            target_lng = target.get("lng", target.get("lon", 0))
            if round(target.get("lat", 0), 5) == round(lat, 5) and round(target_lng, 5) == round(lng, 5):
                if label is None or target.get("label") == label:
                    del targets[i]
                    self.user_profile[key_of_list] = targets
                    self._save_changes(source="profile_manager.remove_by_coords")
                    return True

        return False

    def _save_changes(self, source="profile_manager"):
        self.store.save_profile_guarded(
            self.user_profile,
            expected_revision=self.profile_revision,
            source=source,
            precommit_guard=self.precommit_guard,
        )
        self.reload_profile()

    def get_profile(self, strip_sensitive=False):
        profile = copy.deepcopy(self.user_profile)
        if strip_sensitive:
            for field in ["salt", "password"]:
                profile.pop(field, None)
        return profile

    def get_value(self, key, default=None):
        return self.user_profile.get(key, default)


def authenticate_user(username, password):
    return UserStore().authenticate(username, password)


if __name__ == "__main__":
    mgr = UserProfileManager("admin")
    print(mgr.get_profile())
