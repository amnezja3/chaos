import argparse
import getpass
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import UserStore  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Reset a CHAOS user password.")
    parser.add_argument("username")
    args = parser.parse_args()

    store = UserStore()
    profile = store.get_profile(args.username)
    if not profile:
        raise SystemExit(f"Unknown user: {args.username}")

    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Repeat password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    profile["password"] = password
    profile["salt"] = ""
    store.save_profile(profile)
    print(f"Password updated for: {args.username}")


if __name__ == "__main__":
    main()
