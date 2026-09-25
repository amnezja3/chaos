"""Bounded administrative read models; never hydrate users.profile_json."""
from database import db_connect


def page(db_path, section, *, offset=0, search="", username="", template_id=""):
    offset = max(0, min(int(offset), 1000000))
    search = str(search or "")[:100]
    params = []
    if section == "users":
        query = """SELECT u.username, u.created_at,
                   COALESCE(julianday(u.created_at) BETWEEN julianday('now','-7 days')
                       AND julianday('now'), 0) AS is_new,
                   p.display_alias AS nick, p.clan_code AS clan,
                   p.profession_code AS profession FROM users u
                   LEFT JOIN user_identity_projection p ON p.username=u.username
                   WHERE instr(lower(u.username), lower(?))>0
                      OR instr(lower(COALESCE(p.display_alias,'')), lower(?))>0
                   ORDER BY u.username"""
        params = [search, search]
    elif section == "ghostlab":
        query = """SELECT g.app_id, json_extract(g.app_json,'$.template_id') AS template_id,
            json_extract(g.app_json,'$.name') AS name, g.owner AS author,
            json_extract(g.app_json,'$.icon') AS icon,
            COALESCE(json_extract(g.app_json,'$.downloads'),0) + COALESCE(d.downloads,0) AS downloads,
            json_extract(p.project_json,'$.created_at') AS created_at,
            json_extract(g.app_json,'$.price') AS price_hc,
            CASE WHEN json_extract(g.app_json,'$.published')=1 THEN 'published' ELSE 'withdrawn' END AS status,
            g.artifact_id FROM ghostlab_publications g
            JOIN ghostlab_projects p ON p.app_id=g.app_id AND p.owner=g.owner
            LEFT JOIN googleplex_download_counts d ON d.app_id=g.app_id
            WHERE (instr(lower(g.owner),lower(?))>0 OR instr(lower(json_extract(g.app_json,'$.name')),lower(?))>0)
        """
        params = [search, search]
        if template_id:
            query += " AND json_extract(g.app_json,'$.template_id')=?"
            params.append(template_id)
        query += " ORDER BY g.app_id"
    elif section == "territories":
        query = """SELECT id, owner_username AS owner, area_size, status,
                   centroid_lat AS lat, centroid_lng AS lng, updated_at
                   FROM player_areas WHERE status != 'consumed'
                   AND instr(lower(owner_username),lower(?))>0 ORDER BY id DESC"""
        params = [search]
    elif section == "vulnerabilities":
        query = """SELECT id, label, name, reported_by_username AS reporter,
                   territory_owner_username AS owner, status, target_lat AS lat,
                   target_lng AS lng, updated_at FROM reported_vulnerabilities
                   WHERE (instr(lower(label),lower(?))>0 OR instr(lower(reported_by_username),lower(?))>0)
                   ORDER BY id DESC"""
        params = [search, search]
    elif section == "apps":
        query = """SELECT app_id AS id, substr(json_extract(app_json,'$.name'),1,200) AS name,
                   substr(json_extract(app_json,'$.type'),1,100) AS type, status, updated_at
                   FROM player_apps WHERE username=? AND status != 'uninstalled' ORDER BY app_id"""
        params = [username]
    elif section == "tools":
        query = """SELECT tool_id AS id, app_id, substr(json_extract(tool_json,'$.name'),1,200) AS name,
                   updated_at FROM player_tool_files WHERE username=? ORDER BY tool_id"""
        params = [username]
    elif section == "files":
        query = """SELECT file_id AS id, folder, operation_id, market_status AS status,
                   updated_at FROM player_data_files WHERE username=? ORDER BY file_id"""
        params = [username]
    elif section == "operations":
        query = """SELECT operation_id AS id, operation_type AS type, target_key,
                   status, updated_at FROM player_operations WHERE username=?
                   ORDER BY updated_at DESC, operation_id"""
        params = [username]
    elif section == "captures":
        query = """SELECT lat, lng, substr(json_extract(target_json,'$.label'),1,200) AS name,
                   captured_at FROM captured_targets WHERE owner_username=? ORDER BY captured_at DESC, lat, lng"""
        params = [username]
    else:
        raise ValueError("unknown_admin_section")
    with db_connect(db_path) as conn:
        rows = conn.execute(query + " LIMIT 51 OFFSET ?", (*params, offset)).fetchall()
    return {"items": [dict(row) for row in rows[:50]], "offset": offset,
            "has_more": len(rows) > 50, "page_size": 50}


def user_summary(db_path, username):
    with db_connect(db_path) as conn:
        row = conn.execute("""SELECT p.username, u.created_at, p.display_alias AS nick, p.clan_code AS clan,
            p.profession_code AS profession, w.balance AS hackcoins,
            pos.lat, pos.lng, s.capacity AS storage_capacity, s.used AS storage_used,
            c.player_level AS level,
            json_extract(p.desktop_boot_json,'$.respect') AS respect
            FROM user_identity_projection p JOIN users u ON u.username=p.username
            LEFT JOIN user_capability_projection c ON c.username=p.username
            LEFT JOIN wallet_balances w ON w.username=p.username
            LEFT JOIN player_positions pos ON pos.username=p.username
            LEFT JOIN player_storage s ON s.username=p.username WHERE p.username=?""", (username,)).fetchone()
    return dict(row) if row else None
