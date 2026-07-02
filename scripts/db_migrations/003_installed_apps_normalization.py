try:
    from migration_helpers import normalize_app_contract_fields, normalize_storage, read_profiles, write_profile
except ImportError:
    from scripts.db_migrations.migration_helpers import (
        normalize_app_contract_fields,
        normalize_storage,
        read_profiles,
        write_profile,
    )


MIGRATION_ID = "003"
NAME = "installed apps contract normalization"


def migrate(conn, apply=False):
    scanned = 0
    changed_profiles = 0
    changed_apps = 0
    for item in read_profiles(conn):
        scanned += 1
        profile = item["profile"]
        apps = list(profile.get("apps") or [])
        normalized = []
        profile_changed = False
        for app in apps:
            if not isinstance(app, dict):
                profile_changed = True
                continue
            new_app = normalize_app_contract_fields(app)
            if new_app != app:
                changed_apps += 1
                profile_changed = True
            normalized.append(new_app)
        if profile_changed:
            profile["apps"] = normalized
            normalize_storage(profile)
            changed_profiles += 1
            if apply:
                write_profile(conn, item["username"], profile)
    return {
        "profiles_scanned": scanned,
        "profiles_changed": changed_profiles,
        "apps_normalized": changed_apps,
    }
