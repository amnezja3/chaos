import os
import sys
from pathlib import Path


os.environ.setdefault("CHAOS_DEV_MODE", "true")
os.environ.setdefault("APP_ENV", "staging")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import DevBugReportStore, UserStore  # noqa: E402
from run import app  # noqa: E402


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    user_store = UserStore()
    profiles = user_store.list_profiles()
    usernames = sorted(profile.get("username") for profile in profiles)
    assert_true(usernames == ["admin"], f"Expected only admin user, got: {usernames}")

    admin = user_store.get_profile("admin") or {}
    assert_true(admin.get("hackcoins") == 100000, "Admin HC is not 100000.")
    assert_true(admin.get("level") == 77, "Admin level is not 77.")
    assert_true(admin.get("respect") == 1000, "Admin respect is not 1000.")
    assert_true(not admin.get("operations"), "Admin has runtime operations.")
    assert_true(not admin.get("risk_events"), "Admin has risk events.")
    assert_true(not admin.get("system_messages"), "Admin has system messages.")
    assert_true(not admin.get("market_history"), "Admin has market history.")
    assert_true(not admin.get("targets"), "Admin has targets.")
    assert_true(not admin.get("hacked"), "Admin has hacked targets.")
    assert_true(not admin.get("aimed_target"), "Admin has aimed target.")
    assert_true(all(not value for value in (admin.get("files") or {}).values()), "Admin runtime files are not empty.")
    assert_true(not DevBugReportStore().list_reports(), "Dev bug reports are not empty.")

    client = app.test_client()
    login = client.post("/", data={"username": "admin", "password": "1234"})
    assert_true(login.status_code in {200, 302}, f"Admin login failed with HTTP {login.status_code}.")

    profile_response = client.get("/api/profile")
    assert_true(profile_response.status_code == 200, f"/api/profile HTTP {profile_response.status_code}")
    profile_json = profile_response.get_json() or {}
    assert_true(profile_json.get("username") == "admin", "Profile endpoint did not return admin.")
    assert_true(not profile_json.get("operations"), "Profile endpoint returned operations.")

    resources_response = client.get("/resources.json")
    assert_true(resources_response.status_code == 200, f"/resources.json HTTP {resources_response.status_code}")

    map_response = client.get("/map")
    assert_true(map_response.status_code == 200, f"/map HTTP {map_response.status_code}")

    bug_response = client.get("/api/dev/bug-reports")
    assert_true(bug_response.status_code == 200, f"/api/dev/bug-reports HTTP {bug_response.status_code}")
    bug_json = bug_response.get_json() or {}
    assert_true(bug_json.get("reports") == [], "Bug reporter returned old reports.")

    operations_response = client.get("/api/operations")
    assert_true(operations_response.status_code == 200, f"/api/operations HTTP {operations_response.status_code}")
    operations_json = operations_response.get_json() or {}
    assert_true(operations_json.get("active_operations") == [], "Active operations are not empty.")

    print("Example runtime validation OK")
    print("users:", usernames)
    print("admin:", {"hackcoins": admin.get("hackcoins"), "level": admin.get("level"), "respect": admin.get("respect")})
    print("endpoints:", {
        "login": login.status_code,
        "profile": profile_response.status_code,
        "resources": resources_response.status_code,
        "map": map_response.status_code,
        "dev_bug_reports": bug_response.status_code,
        "operations": operations_response.status_code,
    })


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Example runtime validation FAILED: {exc}", file=sys.stderr)
        raise
