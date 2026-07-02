try:
    from migration_helpers import app_tool_candidates, normalize_storage, read_profiles, tool_file_entry_name, write_profile
except ImportError:
    from scripts.db_migrations.migration_helpers import (
        app_tool_candidates,
        normalize_storage,
        read_profiles,
        tool_file_entry_name,
        write_profile,
    )


MIGRATION_ID = "004"
NAME = "files.tools reconciliation"


def migrate(conn, apply=False):
    scanned = 0
    changed_profiles = 0
    tools_removed = 0
    tools_added = 0
    for item in read_profiles(conn):
        scanned += 1
        profile = item["profile"]
        files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
        tools = list(files.get("tools") or [])
        tool_names = {tool_file_entry_name(entry) for entry in tools}
        expected = set()
        for app in profile.get("apps") or []:
            expected.update(app_tool_candidates(app))

        cleaned = [entry for entry in tools if not tool_file_entry_name(entry).endswith(".sh") or tool_file_entry_name(entry) in expected]
        removed_here = len(tools) - len(cleaned)
        added_here = 0
        for name in sorted(expected - {tool_file_entry_name(entry) for entry in cleaned}):
            if name:
                cleaned.append(name)
                added_here += 1

        if removed_here or added_here:
            tools_removed += removed_here
            tools_added += added_here
            files["tools"] = cleaned
            profile["files"] = files
            normalize_storage(profile)
            changed_profiles += 1
            if apply:
                write_profile(conn, item["username"], profile)
    return {
        "profiles_scanned": scanned,
        "profiles_changed": changed_profiles,
        "tools_removed": tools_removed,
        "tools_added": tools_added,
    }
