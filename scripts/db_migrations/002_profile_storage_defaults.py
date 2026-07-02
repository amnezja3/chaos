try:
    from migration_helpers import normalize_storage, read_profiles, write_profile
except ImportError:
    from scripts.db_migrations.migration_helpers import normalize_storage, read_profiles, write_profile


MIGRATION_ID = "002"
NAME = "profile storage defaults"


def migrate(conn, apply=False):
    scanned = 0
    changed = 0
    for item in read_profiles(conn):
        scanned += 1
        profile = item["profile"]
        before = {
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit"),
            "storage_soft_limit": profile.get("storage_soft_limit"),
            "storage_over_limit": profile.get("storage_over_limit"),
        }
        normalize_storage(profile)
        after = {
            "storage_capacity": profile.get("storage_capacity"),
            "storage_used": profile.get("storage_used"),
            "storage_unit": profile.get("storage_unit"),
            "storage_soft_limit": profile.get("storage_soft_limit"),
            "storage_over_limit": profile.get("storage_over_limit"),
        }
        if before != after:
            changed += 1
            if apply:
                write_profile(conn, item["username"], profile)
    return {"profiles_scanned": scanned, "profiles_changed": changed}
