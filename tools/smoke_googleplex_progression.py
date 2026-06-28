import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from run import app, user_store


def main():
    client = app.test_client()
    login = client.post("/", data={"username": "admin", "password": "1234"})
    if login.status_code not in (200, 302):
        raise SystemExit(f"login failed: {login.status_code}")

    profile_before = client.get("/api/profile").get_json()
    balance_before = int(profile_before.get("hackcoins", 0) or 0)
    catalog = client.get("/resources.json").get_json()
    candidate = next(
        (
            app_data for app_data in catalog
            if not app_data.get("installed")
            and app_data.get("map_actions")
            and int(app_data.get("price") or 0) <= balance_before
        ),
        None,
    )

    if not candidate:
        print("candidate: none")
        print("status: skipped - admin has no affordable uninstalled map-action app")
        return 0

    app_id = candidate["id"]
    print("candidate:", app_id, candidate.get("name"), candidate.get("price"), candidate.get("map_actions"))
    install = client.post("/install-app", json={"app_id": app_id})
    install_data = install.get_json()
    print("install:", install.status_code, install_data.get("status"), install_data.get("message"))
    if install.status_code >= 400 or install_data.get("status") != "success":
        raise SystemExit("install failed")

    profile_after = user_store.get_profile("admin")
    installed = any(app.get("id") == app_id for app in profile_after.get("apps", []))
    tool_name = f"{candidate.get('name')}.sh"
    tools = (profile_after.get("files") or {}).get("tools", [])
    in_tools = tool_name in tools
    balance_after = int(profile_after.get("hackcoins", 0) or 0)
    print("installed:", installed)
    print("tool:", tool_name, in_tools)
    print("hc:", balance_before, "->", balance_after)

    if not installed or not in_tools:
        raise SystemExit("installed app missing from profile.apps or files.tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
