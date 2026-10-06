/* Rebuild the system-owned key register from the shared catalogs. */
const fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const manifest = read('static/locales/manifest.json');
const domains = manifest.domains.map(domain => ({domain, messages:read(`static/locales/pl/${domain}.json`).messages}));
const count = domains.reduce((sum, item) => sum + Object.keys(item.messages).length, 0);
const sources = {
 common:'ghost_i18n.py; ghost_i18n.js — fallback',
 locale:'ghost_i18n_entry.js; createSettings(); /api/profile/desktop',
 entry:'templates/login.html; run.py:index()',
 onboarding:'templates/register.html; register_scripts.js; run.py registration endpoints',
 settings:'terminal.js:createSettings(); run.py settings endpoints',
 profile:'terminal.js:createProfile(); /api/profile/security',
 wallet:'terminal.js wallet renderer; run.py wallet_error_response()',
 session:'session_generation_blocked.html; run.py recovery; login.html',
 terminal:'terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command',
 files:'terminal.js:createFileManager()/runFile()/openFolderInManager()',
 shell:'terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js',
};
const rows = domains.flatMap(({domain,messages}) => Object.entries(messages).sort(([a],[b])=>a.localeCompare(b)).map(([key,entry]) => {
 const spec=Object.entries(entry.params).map(([name,type])=>`${name}: ${type}`).join(', ')||'—';
 const source=sources[key.split('.')[0]];
 if(!source)throw Error('Unclassified key: '+key);
 return `| \`${key}\` | ${domain} | ${spec} | ${source} |`;
}));
const document = `# Sprint 153 — rejestr kluczy i glosariusz

Stan: lokalny odbiór 6 X 2026. **${count} kluczy PL/EN**, pięć domen,
wersja pakietu \`${manifest.content_version}\`. Rejestr generuje
\`node tools/build_i18n_key_register.cjs\`; nie utrzymujemy ręcznie drugiego słownika.

Właściciel wszystkich kluczy: Ghost System. Każdy wynik jest tekstem;
parametry mają jawny typ i są escapowane. Klucze dynamiczne (role, foldery,
zabezpieczenia, operacje) pochodzą wyłącznie z systemowych kodów.
Nieznane nazwy i pochodzenie pozostają dosłowne. \`shell.files.count\`
i \`shell.terminal.welcome\` są wzorcami kontraktu testowanego w obu runtime’ach.

## Granice i wyjątki

- Komendy, ID, receipt, ścieżki, współrzędne techniczne, logi sieciowe i JSON
  pozostają kanoniczne. Formatowanie liczb/dat dotyczy prezentacji.
- Nicki, marki aut, nazwy plików, własne opisy, dokumenty, notatki przelewów
  i historyczne teksty bez jawnego pochodzenia nie podlegają tłumaczeniu.
- FM \`/about\` i \`/tips-tricks\`: oryginały niezmienione, edycje językowe w 155.
- Zawartość narzędzi, aplikacji, instalatora i kreatorów należy do 154;
  narracja, komunikaty trwałe i historia do 155. Powłoka wyświetla systemowe
  etykiety, nie tłumaczy automatycznie zawartości tych produktów.
- Nazwy własne: CHAOS, Ghost System, GhostLab, Googleplex, BlackNet, Cyberner,
  Ghost Hack Radio, Signal Registry, Dev Bug Reporter, AppForge, Term Creator,
  Window Maker, Wallet HC, VIREX, OSM, OpenTopo, Toxic Green, Blue Grid,
  Red Alert, Amber Net, Violet Trace, Secret Path, HC, RSP.

## Glosariusz

| PL | EN | Znaczenie |
| --- | --- | --- |
| Pliki / Menedżer plików | Files / File Manager | Powłoka FM, ścieżki bez zmian |
| Mapa | Map | Etykieta widoku, komenda niezmienna |
| Profil gracza | Player profile | Nick autora pozostaje dosłowny |
| Ustawienia | Settings | Kanoniczny zapis preferencji konta |
| Pełny ekran / Przywróć okno | Fullscreen / Restore window | Stan okna |
| Minimalizuj / Zamknij | Minimize / Close | Istniejące zachowanie workspace |
| Zabezpieczenia | Security | Systemowe kody opcji |
| Saldo / Rezerwacja | Balance / Reserved | Prezentacja, bez zmiany HC |
| Przeznaczenie / Typ operacji | Purpose / Operation type | Etykieta metadanych |
| plik / pliki / plików | file / files | Reguły liczby mnogiej z manifestu |

## Źródła i parametry

Nazwy funkcji odnoszą się do aktualnych rendererów; pełne ścieżki JS:
\`static/js/\`, Python i szablony w katalogu głównym i \`templates/\`.
Odbiór: [raport 153](sprint_153_acceptance.md).

| Klucz | Domena | Parametry | Źródło / renderer |
| --- | --- | --- | --- |
${rows.join('\n')}
`;
fs.writeFileSync(path.join(root,'doc/audits/sprint_153_key_register.md'),document);
console.log(JSON.stringify({content_version:manifest.content_version,keys:count,domains:domains.map(d=>({name:d.domain,keys:Object.keys(d.messages).length}))}));
