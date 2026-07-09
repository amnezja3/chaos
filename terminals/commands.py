from datetime import datetime, timezone
import posixpath
import shlex

from database import JsonResourceStore


resource_store = JsonResourceStore()

CHAOS_HOST = "chaos.node"
CHAOS_CWD = "/home/ghost"

CHAOS_FS = {
    "/": ["home", "var", "etc", "data", "net", "readme.txt"],
    "/home": ["ghost", "ops"],
    "/home/ghost": ["notes.txt", "profile.json", "apps", ".cache"],
    "/home/ghost/apps": ["installed.list", "launcher.hint"],
    "/home/ops": ["briefing.md", "targets.link"],
    "/etc": ["motd", "hosts", "chaos.conf"],
    "/var": ["log", "tmp"],
    "/var/log": ["system.log", "ghost.log", "market.log"],
    "/data": ["camera", "gps", "network", "device", "market"],
    "/net": ["world.channel", "cyberner.link", "ghost_exchange.link"],
}

CHAOS_FILES = {
    "/readme.txt": "CHAOS Terminal surface. Type: help\n",
    "/home/ghost/notes.txt": "Keep routes clean. Watch the map. Trust deltas, verify snapshots.\n",
    "/home/ghost/profile.json": '{ "user": "ghost", "shell": "chaosterm", "mode": "surface" }\n',
    "/home/ghost/apps/installed.list": "Use: apps\nInstalled applications are loaded from your profile.\n",
    "/home/ghost/apps/launcher.hint": "Run an app by typing its name or id.\n",
    "/home/ops/briefing.md": "# Briefing\n- map is live\n- targets remember you\n- Ghost Exchange pays for data\n",
    "/home/ops/targets.link": "map://targets/current\n",
    "/etc/motd": "Welcome to CHAOS. Try: help, status, apps, scan\n",
    "/etc/hosts": "127.0.0.1 localhost\n10.0.13.37 chaos.node\n",
    "/etc/chaos.conf": "terminal=chaosterm\ncyberner=enabled\nghost_exchange=enabled\n",
    "/var/log/system.log": "boot: ok\nprofile: normalized\ndelta-feed: observing\n",
    "/var/log/ghost.log": "radio: signal online\nmap: initial gate armed\nterminal: ready\n",
    "/var/log/market.log": "ghost-exchange: dashboard online\nsettlement: controlled refresh\n",
    "/net/world.channel": "Cyberner source: WORLD\n",
    "/net/cyberner.link": "cyberner://threads\n",
    "/net/ghost_exchange.link": "gx://market/dashboard\n",
}


def _as_profile(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"apps": value}
    return {}


def _apps(profile):
    apps = profile.get("apps", [])
    return apps if isinstance(apps, list) else []


def _username(profile):
    return str(
        profile.get("username")
        or profile.get("login")
        or profile.get("name")
        or "ghost"
    )


def _normalize_path(path):
    if not path or path == ".":
        return CHAOS_CWD
    if not path.startswith("/"):
        path = posixpath.join(CHAOS_CWD, path)
    normalized = posixpath.normpath(path)
    return "/" if normalized == "." else normalized


def _format_help():
    return "\n".join([
        "CHAOS Terminal commands",
        "",
        "Basics:",
        "  help                 show this help",
        "  clear                clear terminal",
        "  echo <text>          print text",
        "  date                 show system time",
        "  whoami               show current user",
        "  uname [-a]           system info",
        "",
        "Filesystem:",
        "  pwd                  print working directory",
        "  ls [path]            list directory",
        "  dir [path]           alias of ls",
        "  cd <path>            validate path hint",
        "  cat <file>           print file",
        "  type <file>          alias of cat",
        "",
        "Runtime:",
        "  status               profile/runtime summary",
        "  scan                 surface diagnostics",
        "  log [system|ghost|market] show recent logs",
        "  apps                 list installed apps",
        "",
        "Session:",
        "  exit / logout        end session",
        "",
        "Tip: run an installed app by typing its name or id.",
    ])


def _list_dir(path):
    normalized = _normalize_path(path)
    entries = CHAOS_FS.get(normalized)
    if entries is None:
        if normalized in CHAOS_FILES:
            return normalized
        return f"ls: cannot access '{path}': no such file or directory"
    return "\n".join(entries)


def _cat_file(path):
    normalized = _normalize_path(path)
    if normalized in CHAOS_FS:
        return f"cat: {normalized}: is a directory"
    if normalized not in CHAOS_FILES:
        return f"cat: {path}: no such file"
    return CHAOS_FILES[normalized].rstrip("\n")


def _status(profile):
    username = _username(profile)
    hackcoins = profile.get("hackcoins", 0)
    storage_used = profile.get("storage_used", 0)
    storage_capacity = profile.get("storage_capacity", 0)
    apps_count = len(_apps(profile))
    files = profile.get("files", {})
    file_count = 0
    if isinstance(files, dict):
        file_count = sum(len(v) for v in files.values() if isinstance(v, list))
    return "\n".join([
        "CHAOS runtime status",
        f"user: {username}",
        f"host: {CHAOS_HOST}",
        f"hackcoins: {hackcoins}",
        f"storage: {storage_used} MB / {storage_capacity} MB",
        f"apps: {apps_count}",
        f"files: {file_count}",
        "cyberner: online",
        "ghost-exchange: online",
    ])


def _scan(profile):
    files = profile.get("files", {})
    market_files = 0
    if isinstance(files, dict):
        for entries in files.values():
            if isinstance(entries, list):
                market_files += sum(1 for entry in entries if isinstance(entry, dict) and entry.get("sellable"))
    return "\n".join([
        "Surface scan complete",
        "- terminal bridge: stable",
        "- map gate: armed",
        "- cyberner route: online",
        f"- market eligible files: {market_files}",
        "Use: status, apps, log system",
    ])


def _apps_list(profile):
    apps = _apps(profile)
    if not apps:
        return "No installed apps."
    lines = ["Installed apps:"]
    for app in apps:
        app_id = app.get("id", "-")
        name = app.get("name", app_id)
        app_type = app.get("type") or app.get("product_type") or "app"
        lines.append(f"- {name} [{app_id}] ({app_type})")
    return "\n".join(lines)


def _log(name):
    aliases = {
        "sys": "system",
        "system": "system",
        "ghost": "ghost",
        "radio": "ghost",
        "gx": "market",
        "market": "market",
    }
    key = aliases.get(name or "system", name or "system")
    path = f"/var/log/{key}.log"
    return _cat_file(path)


def _builtin_command(tokens, original_text, profile):
    if not tokens:
        return {"response": ""}

    cmd = tokens[0].lower()
    arg = tokens[1] if len(tokens) > 1 else ""

    if cmd in {"exit", "logout"}:
        return {"logout": True}
    if cmd == "clear":
        return {"clear": True}
    if cmd == "help":
        return {"response": _format_help()}
    if cmd == "echo":
        return {"response": original_text.partition(" ")[2]}
    if cmd == "date":
        return {"response": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
    if cmd == "whoami":
        return {"response": _username(profile)}
    if cmd == "uname":
        full = " -a" if "-a" in tokens[1:] else ""
        if full:
            return {"response": "CHAOS chaosterm 7.09 ghost-kernel delta-feed x86_64"}
        return {"response": "CHAOS"}
    if cmd == "pwd":
        return {"response": CHAOS_CWD}
    if cmd in {"ls", "dir"}:
        return {"response": _list_dir(arg or CHAOS_CWD)}
    if cmd == "cd":
        target = _normalize_path(arg)
        if target in CHAOS_FS:
            return {"response": f"cwd hint: {target}\nSession cwd persistence is not enabled yet."}
        return {"response": f"cd: {arg or ''}: no such directory"}
    if cmd in {"cat", "type"}:
        if not arg:
            return {"response": f"{cmd}: missing file operand"}
        return {"response": _cat_file(arg)}
    if cmd == "status":
        return {"response": _status(profile)}
    if cmd == "scan":
        return {"response": _scan(profile)}
    if cmd == "log":
        return {"response": _log(arg or "system")}
    if cmd == "apps":
        return {"response": _apps_list(profile)}
    if cmd in {"unlock", "su", "daemon", "lore"}:
        return {"response": f"{cmd}: channel locked. Future story runtime will attach here."}

    return None


def interpret_command(text, user_profile):
    original_text = str(text or "").strip()
    lowered = original_text.lower()
    profile = _as_profile(user_profile)

    if not original_text:
        return {"response": ""}

    try:
        tokens = shlex.split(original_text)
    except ValueError as exc:
        return {"response": f"parse error: {exc}"}

    if len(tokens) == 3 and tokens[0].lower() == "sudo" and tokens[1].lower() == "userdel":
        return {"confirm_userdel": tokens[2]}

    builtin = _builtin_command(tokens, original_text, profile)
    if builtin is not None:
        return builtin

    terminal_data = resource_store.get(
        "terminal_command",
        default={}
    )

    if terminal_data and lowered in terminal_data:
        cmd = terminal_data[lowered]
        if cmd.get("type") == "system":
            return {"response": cmd.get("result", "Brak odpowiedzi.")}

    matching_app = next(
        (
            app for app in _apps(profile)
            if str(app.get("name", "")).lower() == lowered
            or str(app.get("id", "")).lower() == lowered
        ),
        None
    )
    if matching_app:
        return {"runApp": matching_app["id"]}

    return {"response": f"Nieznana komenda: {lowered}"}
