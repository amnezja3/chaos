"""Reviewed system seed presentation. Never classify a tool by its display name."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The ordered text fields exclude commands, action IDs, effects, prices and paths.
EN = {
 'scan_probe_v1': ['An active probe detecting ports and user locations. Active protection may detect it.',
  'ScanProbe — Active port and location scan', 'Initializing probe…', 'Resolving IP address…', 'Checking open ports…', 'Analyzing user geolocation…', '✅ Open ports and approximate location identified.', '❌ Scan interrupted or blocked.'],
 'deep_sniff_r2': ['A deep scanner analyzing running processes and security logs. Active logging or log integrity protection may block it.',
  'DeepSniff — Process and log analysis', 'Connecting to system…', 'Reading active tasks…', 'Checking log integrity…', 'Collecting suspicious entries…', '✅ Active tasks and suspicious log entries detected.', '❌ Could not access logs or processes.'],
 'ghost_ping_x3': ['A lightweight scanner detecting users on the network and flaws in their camouflage. Advanced anomaly detection may detect it.',
  'GhostPing — Pinging hidden devices', 'Sending ping…', 'Waiting for responses…', 'Analyzing network responses…', 'Checking camouflage flaws…', '✅ Hidden users and masking flaws detected.', '❌ No response — devices may be out of range or well hidden.'],
 'stealth_browser_v2': ['A minimal browser with a hidden referrer and no history. Vulnerable to active browser protection.',
  'StealthBrowser v2 — Hidden mode', '🌐 Default page: xhttp://start.local', '🔒 Referrer hidden: YES', '📜 Browsing history: OFF', '🛡️ Script blocking: ACTIVE', 'Open new tab', 'Close browser'],
 'crypto_vault_v1': ['An encrypted file explorer. Hides contents from the system and file analysis.',
  'Encrypted File Vault — Encrypted access', '📁 Folder: /vault', '🧾 File: log.txt — 🔐 encrypted', '🧾 File: secrets.dat — 🔐 encrypted', '🔄 File indexing: OFF', '👁️ System visibility: HIDDEN', 'Decrypt files', 'Close vault'],
 'phantom_vpn_v1': ['An automatically switching VPN tunnel. Masks player activity but may conflict with TCP/IP session exploit injection.',
  'Establishing VPN Tunnel', 'Negotiating encryption parameters...', 'Assigning virtual IP address...', 'Securing communication channel...', 'Finalizing tunnel handshake...', 'VPN tunnel established successfully. IP masked.', 'VPN connection failed. Check for VPN blockers or network issues.'],
 'shadow_layer_v1': ['A layer masking player actions in the system. Reduces visibility but limits active system features.',
  'Choose concealment mode:', 'ShadowLayer hides system activity. Choose a concealment level — deeper concealment carries a greater risk of disabling features.', 'Passive — log masking only', 'Aggressive — full isolation', 'Quiet tunnel — hide network activity', 'Idle simulation — disguise activity as idle', 'Deep Phantom Mode — full kernel separation (EXPERIMENTAL)', 'Cancel'],
 'injector_x_v1': ['An advanced exploit injection tool. Works only with kernel protection disabled. May reduce system integrity.',
  'Connecting to target service…', 'Attempting to bypass kernel protection…', 'Code injection successful.', 'System integrity: -15%', 'Connecting to target service…', 'Firewall core active — access blocked!', 'Injection failed.'],
 'procmon_v1': ['A system process monitor. Detects unauthorized applications and activity but may limit offensive tools.',
  'Process monitor', 'PID: 2331 | Name: injector_x_v1 | Status: Injection attempt detected', 'PID: 4522 | Name: shadow_layer_v1 | Status: Hidden process — threat', 'PID: 1090 | Name: trusted_daemon | Status: OK', 'Terminate process', 'Ignore'],
 'drivecrypt_v1': ['A filesystem encryption module. Protects player data but affects performance and may conflict with indexing tools.',
  'DriveEncryptor — Disk encryption', '🔐 Initializing DriveEncryptor…', '🔄 Scanning directory structures…', '🗂️ Securing user data…', '💾 Overwriting unencrypted sectors…', '✅ All data encrypted successfully.', '❌ Encryption did not complete successfully.'],
 'zeroday_hunter': ['An advanced zero-day vulnerability detector. May reveal unknown attack vectors but is easily detected by active monitoring.',
  'run launch zeroday_scan deep verbose', 'check vulnerabilities 0day', 'report generate format json'],
 'mem_overflow_v1': ['A memory overflow attack. Effective when memory protections are disabled; may damage the target system or the player’s own system.',
  'MemoryOverflow — Memory overflow', '📤 Sending test data…', '💽 Exceeding buffer boundary…', '📉 Manipulating RAM allocation…', '🧠 Initializing memory overflow…', '💥 Memory overloaded — exploit successful.', '⚠️ Attack detected and blocked. Process restarted by the system.'],
 'pencombo_v1': ['A combined penetration toolkit for automated reconnaissance, privilege escalation and code injection across system attack vectors.',
  'Choose PenCombo attack mode:', 'An integrated penetration toolkit. Match the mode to your target, from scanning to code injection.', 'Recon Mode — passive analysis and weakness detection', 'Injection Mode — active code injection', 'Privilege Escalation — escalation from low privileges', 'All-In-One Strike — full penetration sequence', 'Hack that all'],
 'camstream_v1': ['A remote IP camera viewer. Stealthy, but may trigger a surveillance system alert.',
  'CamStream — Camera view', '🔍 Searching for active cameras…', '📡 Connecting…', '🖼️ Streaming video…', '📁 Buffering video data…', '✅ Camera image acquired. Object under observation.', '❌ Camera rejected the connection. Active protection may be present.'],
 'camdisabler_v1': ['A tool for disabling and disrupting IP cameras. Leaves log traces unless used in stealth mode.',
  'Connecting to camera…', 'Attempting to disable active stream…', 'Disrupting video signal transmission…', '✅ Camera deactivated.', 'Scanning open camera ports…', 'Injecting disruptive code…', '⚠️ Active protection detected — operation interrupted.'],
 'micsniff_v1': ['A microphone sniffer for quiet environmental listening. Detects conversations or sounds around the target.',
  'MicSniff — Microphone listening', '📡 Searching for active microphones…', '🎧 Listening to audio channel…', '📥 Analyzing sound levels…', '📤 Decrypting audio stream…', '✅ Audio captured. Conversation may be active.', '❌ No audio source or audio blocked.'],
 'bttracer_v1': ['A scanner for active nearby Bluetooth devices. Useful for tracking a user or their equipment.',
  'BTTracer — BLE signal scan', '📡 Detecting active beacons…', '🔍 Analyzing RSSI signal…', '📍 Locating devices…', '📲 Reading MAC identifiers…', '✅ Nearby Bluetooth devices found.', '❌ No active devices or signal disrupted.'],
 'gpsprobe_v1': ['A GPS probe locating moving objects. Remotely determines target coordinates.',
  'GPSProbe — Location detection', '🔎 Locating GPS signal…', '📍 Connecting to satellite…', '🛰️ Synchronizing location data…', '📡 Receiving coordinates…', '✅ GPS position established. Tracking target.', '❌ No GPS signal or heavy interference.'],
 'wifibreaker_v1': ['Break into a Wi-Fi network to access local infrastructure or listen to traffic.',
  'WiFiBreaker — Breaking protection', '🔐 Reading signal…', '📡 Attempting authentication…', '🧬 Analyzing WPA2 password…', '🔓 Protection breached!', '✅ Wi-Fi access obtained.', '❌ Attempt failed. Strong encryption.'],
 'data_corruptor_v1': ['Sabotage the victim’s files and data: logs, archives and database dumps.',
  'Corrupting data…', '📂 Searching for sensitive files…', '🧨 Introducing CRC errors…', '📉 Removing backups…', '💥 Sabotage complete', '✅ Data corrupted. System destabilized.', '❌ Could not breach the system — active security monitoring.'],
}


def fields(product):
    yield 'description', product['description']
    for i, level in enumerate(product.get('levels', [])):
        for name, value in level.items():
            prefix = f'levels.{i}.{name}'
            if name in ('title', 'text', 'result_success', 'result_failure'):
                yield prefix, value
            elif name in ('steps', 'logs', 'list'):
                for j, text in enumerate(value):
                    yield f'{prefix}.{j}', text
            elif name in ('options', 'buttons'):
                for j, option in enumerate(value):
                    yield f'{prefix}.{j}.label', option['label']


PL_OVERRIDES = {
    'phantom_vpn_v1': {
        'levels.0.title': 'Nawiązywanie tunelu VPN',
        'levels.0.steps.0': 'Negocjowanie parametrów szyfrowania…',
        'levels.0.steps.1': 'Przydzielanie wirtualnego adresu IP…',
        'levels.0.steps.2': 'Zabezpieczanie kanału komunikacji…',
        'levels.0.steps.3': 'Kończenie uzgadniania tunelu…',
        'levels.0.result_success': 'Tunel VPN nawiązany. Adres IP zamaskowany.',
        'levels.0.result_failure': 'Połączenie VPN nieudane. Sprawdź blokady VPN i połączenie sieciowe.',
    },
}


def main():
    source = json.loads((ROOT / 'static/app_config.json').read_text(encoding='utf8'))
    products = {p['id']: p for p in source if p['id'] in EN}
    if products.keys() != EN.keys():
        raise ValueError('Reviewed system seeds missing')
    registry = {}
    catalogs = {l: json.loads((ROOT / f'static/locales/{l}/catalog.json').read_text(encoding='utf8')) for l in ('pl', 'en')}
    for product_id, product in products.items():
        owned_fields = list(fields(product))
        if len(owned_fields) != len(EN[product_id]):
            raise ValueError(f'Review changed text fields for {product_id}')
        registry[product_id] = {'name': product['name'], **dict(owned_fields)}
        for path, pl, en in [('name', product['name'], product['name'])] + [
                (path, pl, en) for (path, pl), en in zip(owned_fields, EN[product_id])]:
            pl = PL_OVERRIDES.get(product_id, {}).get(path, pl)
            for locale, text in [('pl', pl), ('en', en)]:
                catalogs[locale]['messages'][f'catalog.system.{product_id}.{path}'] = {'params': {}, 'text': text}
    for locale, data in catalogs.items():
        (ROOT / f'static/locales/{locale}/catalog.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    (ROOT / 'static/locales/system_app_sources.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(f'{len(registry)} reviewed legacy system applications')


if __name__ == '__main__':
    main()
