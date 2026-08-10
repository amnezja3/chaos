from datetime import datetime, timezone
import hashlib
import posixpath
import shlex
import re

from database import JsonResourceStore


resource_store = JsonResourceStore()

CHAOS_HOST = "chaos.node"
CHAOS_CWD = "/home/ghost"
COORDINATE_PAIR_RE = re.compile(r"^\s*([+-]?\d+(?:[\.,]\d+)?)\s*[:;,]\s*([+-]?\d+(?:[\.,]\d+)?)\s*$")

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

SYSTEM_APP_ALIASES = {
    "mapa": "map",
    "map": "map",
    "operation": "map",
    "operations": "map",
    "oprations": "map",
    "motobike": "map",
    "hack": "map",
    "hacking": "map",
    "game": "map",
    "start": "map",
    "internet": "browser",
    "web": "browser",
    "www": "browser",
    "browser": "browser",
    "googleplex": "browser",
    "gp": "browser",
    "ghostexchange": "browser",
    "gx": "browser",
    "sell": "browser",
    "sellfiles": "browser",
    "market": "browser",
    "stockmarket": "browser",
    "stock": "browser",
    "wallet": "wallet",
    "hackcont": "wallet",
    "hackcoin": "wallet",
    "con": "wallet",
    "coins": "wallet",
    "money": "wallet",
    "tranfer": "wallet",
    "transfer": "wallet",
    "sendmoney": "wallet",
    "sendhc": "wallet",
    "sendhackcoin": "wallet",
    "portfel": "wallet",
    "muzyka": "radio",
    "radio": "radio",
    "music": "radio",
    "ghosradio": "radio",
    "ghostradio": "radio",
    "poczta": "cyberner",
    "komunikator": "cyberner",
    "mail": "cyberner",
    "mailbox": "cyberner",
    "cyberner": "cyberner",
    "friends": "cyberner",
    "world": "cyberner",
    "clan": "cyberner",
    "crew": "cyberner",
    "message": "cyberner",
    "files": "files",
    "pliki": "files",
    "folder": "files",
    "storage": "files",
    "dysk": "files",
    "profil": "profile",
    "profile": "profile",
    "about": "profile",
    "mychaos": "profile",
    "chaos": "profile",
    "ustawienia": "settings",
    "settings": "settings",
    "devbugs": "devbugs",
    "bugs": "devbugs",
    "reporter": "devbugs",
    "bugreporter": "devbugs",
    "error": "devbugs",
    "dev": "devbugs",
    "blad": "devbugs",
    "zglos": "devbugs",
}

SYSTEM_APP_LABELS = {
    "map": "mape",
    "browser": "Browser",
    "wallet": "Wallet HC",
    "radio": "Ghost Hack Radio",
    "cyberner": "Cyberner",
    "files": "Pliki",
    "profile": "Profil",
    "settings": "Ustawienia",
    "devbugs": "Dev Bug Reporter",
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


def _stable_number(seed, minimum=1, maximum=254):
    digest = hashlib.sha1(str(seed).encode("utf-8")).hexdigest()
    span = max(1, maximum - minimum + 1)
    return minimum + (int(digest[:8], 16) % span)


def _pseudo_ip(seed, private=True):
    if private:
        return "10.{}.{}.{}".format(
            _stable_number(f"{seed}:a", 13, 42),
            _stable_number(f"{seed}:b", 1, 254),
            _stable_number(f"{seed}:c", 2, 240),
        )
    return "77.{}.{}.{}".format(
        _stable_number(f"{seed}:a", 10, 240),
        _stable_number(f"{seed}:b", 1, 254),
        _stable_number(f"{seed}:c", 2, 240),
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
        "  map/browser/files/profile/settings open system apps",
        "  teleport <lat:lon>   teleport to coordinates",
        "  teleport cur:loc     teleport to device location",
        "",
        "Network:",
        "  ip / ipa / ip a      show pseudo interface state",
        "  ifconfig             show pseudo interface state",
        "  ping <host>          simulated latency probe",
        "  traceroute <host>    simulated route",
        "  nslookup <host>      simulated DNS lookup",
        "  netstat              simulated socket table",
        "",
        "Session:",
        "  exit                 close terminal window",
        "  logout               logout from game",
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


def _ip_addr(profile):
    username = _username(profile)
    ip = _pseudo_ip(username)
    public_ip = _pseudo_ip(f"{username}:wan", private=False)
    return "\n".join([
        "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536",
        "    inet 127.0.0.1/8 scope host lo",
        "2: ghost0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500",
        f"    inet {ip}/24 scope global ghost0",
        f"    inet6 fd13:37::{_stable_number(username, 100, 999)}/64 scope ghost",
        "3: tunnel0: <POINTOPOINT,UP,LOWER_UP> mtu 1380",
        f"    inet {public_ip}/32 scope ghost tunnel0",
    ])


def _ifconfig(profile):
    username = _username(profile)
    return "\n".join([
        "ghost0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST> mtu 1500",
        f"        inet {_pseudo_ip(username)} netmask 255.255.255.0 broadcast 10.42.255.255",
        f"        ether 02:13:37:{_stable_number(username, 10, 99):02d}:{_stable_number(username + ':x', 10, 99):02d}:{_stable_number(username + ':y', 10, 99):02d}",
        "tunnel0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP> mtu 1380",
        f"        inet {_pseudo_ip(username + ':wan', private=False)} netmask 255.255.255.255",
    ])


def _ping(target):
    host = target or CHAOS_HOST
    ip = _pseudo_ip(host, private=False)
    header = f"PING {host} ({ip}) 56(84) bytes of data."
    lines = [header]
    for seq in range(1, 5):
        sample = f"64 bytes from {ip}: icmp_seq={seq} ttl={_stable_number(host + ':ttl', 48, 63)}"
        latency = (len(header) + len(sample) + _stable_number(f"{host}:{seq}", 1, 80)) / 10
        lines.append(f"{sample} time={latency:.1f} ms")
    avg = sum((len(line) + _stable_number(f"{host}:avg:{idx}", 1, 40)) / 10 for idx, line in enumerate(lines[1:], 1)) / 4
    lines.extend([
        "",
        f"--- {host} ping statistics ---",
        "4 packets transmitted, 4 received, 0% packet loss",
        f"rtt min/avg/max = {max(1.0, avg - 2.1):.1f}/{avg:.1f}/{avg + 3.4:.1f} ms",
    ])
    return "\n".join(lines)


def _traceroute(target):
    host = target or CHAOS_HOST
    hops = [
        ("ghost-gw.local", _pseudo_ip("gateway")),
        ("relay.blacknet", _pseudo_ip("blacknet", private=False)),
        ("edge.ghost.exchange", _pseudo_ip("ghost-exchange", private=False)),
        (host, _pseudo_ip(host, private=False)),
    ]
    lines = [f"traceroute to {host} ({hops[-1][1]}), 30 hops max"]
    for index, (name, ip) in enumerate(hops, 1):
        t1 = (_stable_number(f"{host}:{index}:1", 5, 120) + len(name)) / 10
        t2 = t1 + (_stable_number(f"{host}:{index}:2", 1, 20) / 10)
        t3 = t2 + (_stable_number(f"{host}:{index}:3", 1, 20) / 10)
        lines.append(f"{index:2d}  {name} ({ip})  {t1:.1f} ms  {t2:.1f} ms  {t3:.1f} ms")
    return "\n".join(lines)


def _nslookup(target):
    host = target or CHAOS_HOST
    return "\n".join([
        "Server:  chaos.resolver",
        f"Address: {_pseudo_ip('resolver')}",
        "",
        f"Name:    {host}",
        f"Address: {_pseudo_ip(host, private=False)}",
    ])


def _netstat(profile):
    username = _username(profile)
    local_ip = _pseudo_ip(username)
    return "\n".join([
        "Proto Local Address          Foreign Address        State",
        f"tcp   {local_ip}:22          {_pseudo_ip('admin', private=False)}:53118 ESTABLISHED",
        f"tcp   {local_ip}:443         {_pseudo_ip('ghost-exchange', private=False)}:443 ESTABLISHED",
        f"udp   {local_ip}:5353        224.0.0.251:5353      LISTEN",
        "tcp   127.0.0.1:6666         127.0.0.1:0          LISTEN",
    ])


def _builtin_command(tokens, original_text, profile):
    if not tokens:
        return {"response": ""}

    cmd = tokens[0].lower()
    arg = tokens[1] if len(tokens) > 1 else ""

    if cmd == "exit":
        return {"close_terminal": True, "response": "Zamykanie terminala..."}
    if cmd == "logout":
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
    if cmd == "teleport":
        coord_arg = original_text.partition(" ")[2].strip()
        if not coord_arg:
            return {"response": "usage: teleport <lat:lon|cur:loc>"}
        if coord_arg.lower() == "cur:loc":
            return {
                "terminalGeolocationRequest": {
                    "purpose": "teleport",
                    "label": "Aktualna lokalizacja urzadzenia",
                },
                "response": "Oczekiwanie na zgode dostepu do lokalizacji...",
            }
        match = COORDINATE_PAIR_RE.match(coord_arg)
        if not match:
            return {"response": "teleport: podaj wspolrzedne w formacie lat:lon, np. teleport 52.2297:21.0122"}
        try:
            lat = float(match.group(1).replace(",", "."))
            lng = float(match.group(2).replace(",", "."))
        except ValueError:
            return {"response": "teleport: nieprawidlowe wspolrzedne."}
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return {"response": "teleport: wspolrzedne poza zakresem."}
        return {
            "terminalTeleport": {
                "lat": lat,
                "lng": lng,
                "label": f"{lat:.6f}, {lng:.6f}"
            },
            "response": f"Przygotowano teleport do: {lat:.6f}, {lng:.6f}"
        }
    if cmd in SYSTEM_APP_ALIASES:
        app_key = SYSTEM_APP_ALIASES[cmd]
        label = SYSTEM_APP_LABELS.get(app_key, app_key)
        return {
            "openSystemApp": app_key,
            "response": f"Otwieram {label}..."
        }
    if cmd in {"ip", "ipa"}:
        if cmd == "ip" and len(tokens) > 1 and tokens[1].lower() not in {"a", "addr", "address"}:
            return {"response": "usage: ip a"}
        return {"response": _ip_addr(profile)}
    if cmd == "ifconfig":
        return {"response": _ifconfig(profile)}
    if cmd == "hostname":
        return {"response": CHAOS_HOST}
    if cmd == "ping":
        return {"response": _ping(arg)}
    if cmd in {"traceroute", "tracepath"}:
        return {"response": _traceroute(arg)}
    if cmd in {"nslookup", "dig"}:
        return {"response": _nslookup(arg)}
    if cmd in {"netstat", "ss"}:
        return {"response": _netstat(profile)}
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
