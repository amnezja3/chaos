import copy

from database import JsonResourceStore, UserStore


class UserProfileManager:
    def __init__(self, username, users_path="static/users.json", template_path="static/user_template.json"):
        self.username = username
        self.users_path = users_path
        self.template_path = template_path
        self._locked_keys = {"username", "salt", "password"}
        self._dynamic_profile_keys = {"googleplex_products", "product_purchases", "storage_upgrades"}
        self.store = UserStore(seed_path=users_path)
        self.resource_store = JsonResourceStore()
        self._load_all_users()
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
            self._save_changes()

    def _recursive_sync(self, user_data: dict, template_data: dict, path=()) -> bool:
        updated = False

        for key, template_value in template_data.items():
            if key not in user_data:
                user_data[key] = copy.deepcopy(template_value)
                updated = True
            elif isinstance(template_value, dict) and isinstance(user_data[key], dict):
                updated = self._recursive_sync(user_data[key], template_value, path + (key,)) or updated

        if path == ("desktop_settings", "icon_positions"):
            return updated

        keys_to_remove = [
            key for key in user_data
            if key not in template_data and key not in self._locked_keys and key not in self._dynamic_profile_keys
        ]
        for key in keys_to_remove:
            del user_data[key]
            updated = True

        return updated

    def _load_all_users(self):
        self.all_users = self.store.list_profiles()

    def _find_user_profile(self):
        profile = self.store.get_profile(self.username)
        if not profile:
            raise ValueError(f"User '{self.username}' not found.")

        self.user_profile = profile
        self.original_profile = copy.deepcopy(profile)

    def add_new_user(self, new_username: str, password: str, template_path="static/user_template.json", overwrite=False):
        existing_user = self.store.get_profile(new_username)

        if existing_user and not overwrite:
            raise ValueError(f"Użytkownik '{new_username}' już istnieje.")

        template = self._load_template(template_path)
        template["username"] = new_username
        template["password"] = password
        template["salt"] = "generated_salt_here"

        self.store.save_profile(template)
        self._load_all_users()
        return True

    def reload_profile(self):
        self._load_all_users()
        self._find_user_profile()

    def update_profile(self, updates: dict):
        for key, new_value in updates.items():
            if key in self._locked_keys:
                continue

            if key in self.user_profile:
                original_type = type(self.user_profile[key])
                if isinstance(new_value, original_type):
                    self.user_profile[key] = new_value
                else:
                    raise TypeError(f"Typ wartości dla '{key}' musi być {original_type.__name__}.")
            else:
                self.user_profile[key] = new_value

        self._save_changes()

    def update_profile_value(self, profile_key: str, new_value):
        if profile_key in self._locked_keys:
            raise PermissionError(f"Nie można edytować klucza chronionego: {profile_key}")

        if profile_key not in self.user_profile:
            raise KeyError(f"Klucz '{profile_key}' nie istnieje w profilu użytkownika.")

        current_value = self.user_profile[profile_key]
        current_type = type(current_value)

        if isinstance(current_value, list):
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

        self._save_changes()

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
                self._save_changes()
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
                    self._save_changes()
                    return True

        return False

    def _save_changes(self):
        self.store.save_profile(self.user_profile)
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
