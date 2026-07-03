import argparse
from collections import Counter, defaultdict

from database import db_connect, loads_json
from run import conflict_area_key, normalize_player_area


def load_areas(username=None):
    query = "SELECT * FROM player_areas"
    params = []
    if username:
        query += " WHERE owner_username = ?"
        params.append(username)
    query += " ORDER BY owner_username, id"
    with db_connect() as conn:
        return conn.execute(query, params).fetchall()


def load_encircled_events(username=None):
    query = """
        SELECT id, area_id, owner_username, actor_username, event_type, payload_json, created_at
        FROM area_events
        WHERE event_type = 'area_encircled'
    """
    params = []
    if username:
        query += " AND owner_username = ?"
        params.append(username)
    query += " ORDER BY owner_username, id"
    with db_connect() as conn:
        return conn.execute(query, params).fetchall()


def main():
    parser = argparse.ArgumentParser(description="Read-only territory diagnostic for encircled-area regressions.")
    parser.add_argument("--username", default="", help="Optional owner username to inspect.")
    args = parser.parse_args()
    username = args.username.strip() or None

    invalid = []
    valid = []
    status_counts = Counter()
    owner_counts = Counter()

    for row in load_areas(username):
        raw_area = {
            "id": row["id"],
            "owner_username": row["owner_username"],
            "vertices": loads_json(row["vertices_json"], []),
            "centroid_lat": row["centroid_lat"],
            "centroid_lng": row["centroid_lng"],
            "area_size": row["area_size"],
            "max_edge_distance": row["max_edge_distance"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        clean = normalize_player_area(raw_area)
        if not clean:
            invalid.append(raw_area)
            continue
        valid.append(clean)
        status_counts[clean["status"]] += 1
        owner_counts[clean["owner_username"]] += 1

    events_by_area_key = defaultdict(list)
    events_without_key = []
    for row in load_encircled_events(username):
        payload = loads_json(row["payload_json"], {})
        area_key = payload.get("area_key")
        event = {
            "id": row["id"],
            "area_id": row["area_id"],
            "owner_username": row["owner_username"],
            "created_at": row["created_at"],
            "area_key": area_key,
        }
        if area_key:
            events_by_area_key[(row["owner_username"], area_key)].append(event)
        else:
            events_without_key.append(event)

    print("Territory diagnostic")
    print("username:", username or "*")
    print("valid_areas:", len(valid))
    print("invalid_areas:", len(invalid))
    print("status_counts:", dict(status_counts))
    print("owner_counts:", dict(owner_counts))

    if invalid:
        print("\nInvalid areas:")
        for area in invalid[:50]:
            print(" ", {
                "id": area.get("id"),
                "owner_username": area.get("owner_username"),
                "status": area.get("status"),
                "vertices_count": len(area.get("vertices") or []),
            })

    encircled = [area for area in valid if area.get("status") == "encircled"]
    if encircled:
        print("\nEncircled areas:")
        for area in encircled[:50]:
            print(" ", {
                "id": area.get("id"),
                "owner_username": area.get("owner_username"),
                "area_key": conflict_area_key(area),
                "area_size": area.get("area_size"),
            })

    duplicates = {
        key: events
        for key, events in events_by_area_key.items()
        if len(events) > 1
    }
    print("\nencircled_events_with_area_key:", sum(len(events) for events in events_by_area_key.values()))
    print("encircled_events_without_area_key:", len(events_without_key))
    print("duplicate_area_key_events:", len(duplicates))
    for key, events in list(duplicates.items())[:50]:
        print(" ", key, "count:", len(events), "ids:", [event["id"] for event in events])


if __name__ == "__main__":
    main()
