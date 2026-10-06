# Sprint 153 — rejestr kluczy i glosariusz

Stan: lokalny odbiór 6 X 2026. **496 kluczy PL/EN**, pięć domen,
wersja pakietu `153.4`. Rejestr generuje
`node tools/build_i18n_key_register.cjs`; nie utrzymujemy ręcznie drugiego słownika.

Właściciel wszystkich kluczy: Ghost System. Każdy wynik jest tekstem;
parametry mają jawny typ i są escapowane. Klucze dynamiczne (role, foldery,
zabezpieczenia, operacje) pochodzą wyłącznie z systemowych kodów.
Nieznane nazwy i pochodzenie pozostają dosłowne. `shell.files.count`
i `shell.terminal.welcome` są wzorcami kontraktu testowanego w obu runtime’ach.

## Granice i wyjątki

- Komendy, ID, receipt, ścieżki, współrzędne techniczne, logi sieciowe i JSON
  pozostają kanoniczne. Formatowanie liczb/dat dotyczy prezentacji.
- Nicki, marki aut, nazwy plików, własne opisy, dokumenty, notatki przelewów
  i historyczne teksty bez jawnego pochodzenia nie podlegają tłumaczeniu.
- FM `/about` i `/tips-tricks`: oryginały niezmienione, edycje językowe w 155.
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
`static/js/`, Python i szablony w katalogu głównym i `templates/`.
Odbiór: [raport 153](sprint_153_acceptance.md).

| Klucz | Domena | Parametry | Źródło / renderer |
| --- | --- | --- | --- |
| `common.unavailable` | foundation | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `locale.invalid` | foundation | — | ghost_i18n_entry.js; createSettings(); /api/profile/desktop |
| `locale.label` | foundation | — | ghost_i18n_entry.js; createSettings(); /api/profile/desktop |
| `locale.load_failed` | foundation | — | ghost_i18n_entry.js; createSettings(); /api/profile/desktop |
| `locale.saved` | foundation | — | ghost_i18n_entry.js; createSettings(); /api/profile/desktop |
| `locale.test_notice` | foundation | — | ghost_i18n_entry.js; createSettings(); /api/profile/desktop |
| `shell.desktop.files` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.desktop.map` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.desktop.profile` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.desktop.settings` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.files.count` | foundation | count: number | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.terminal.welcome` | foundation | name: string | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.window.close` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.window.maximize` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.window.minimize` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.window.restore` | foundation | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `locale.save_failed` | settings | — | ghost_i18n_entry.js; createSettings(); /api/profile/desktop |
| `settings.account` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.account_hint` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.auto_fullscreen` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.change_password` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.current_password` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.display` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.email` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.email_failed` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.email_saved` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.email_saving` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.fullscreen_off` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.fullscreen_on` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.map_failed` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.map_saved` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.map_saving` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.map_scheme` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.map_unconfirmed` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.new_password` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.none` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.password_failed` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.password_hint` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.password_saved` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.password_saving` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.radio_autoplay` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.radio_off` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.radio_on` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.runtime` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.save_email` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.screen_mode` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx_failed` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx_hint` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx_off` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx_on` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx_playing` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.sfx_unavailable` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.volume` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.wallpaper` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.wallpaper_saved` | settings | — | terminal.js:createSettings(); run.py settings endpoints |
| `entry.authorize` | entry | — | templates/login.html; run.py:index() |
| `entry.description` | entry | — | templates/login.html; run.py:index() |
| `entry.invalid_credentials` | entry | — | templates/login.html; run.py:index() |
| `entry.no_account` | entry | — | templates/login.html; run.py:index() |
| `entry.password` | entry | — | templates/login.html; run.py:index() |
| `entry.password_hint` | entry | — | templates/login.html; run.py:index() |
| `entry.register` | entry | — | templates/login.html; run.py:index() |
| `entry.submit` | entry | — | templates/login.html; run.py:index() |
| `entry.username` | entry | — | templates/login.html; run.py:index() |
| `onboarding.back` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.choose_faction` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.choose_role` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.confirm_password` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.confirm_placeholder` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.email` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.email_hint` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.email_invalid` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.email_taken` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction_first` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction_required` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.1.name` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.1.summary` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.2.name` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.2.summary` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.3.name` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.3.summary` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.4.name` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.faction.4.summary` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.failed` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.finish` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.identity_invalid` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.installing` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.installing_profile` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.network` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.next` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.nick` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.nick_invalid` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.nick_placeholder` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.not_selected` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_digit` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_hint` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_letter` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_long` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_mismatch` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_placeholder` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.password_short` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.required` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role_hint` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role_required` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.1.1` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.1.2` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.1.3` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.1.4` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.1.5` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.2.1` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.2.2` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.2.3` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.2.4` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.2.5` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.3.1` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.3.2` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.3.3` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.3.4` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.3.5` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.4.1` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.4.2` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.4.3` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.4.4` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.role.4.5` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.selected` | onboarding | name: string | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.setup` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.spawn_failed` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.0.text` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.0.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.1.text` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.1.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.2.text` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.2.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.3.text` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.3.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.4.text` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.4.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.5.text` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.story.5.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.summary_email` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.summary_faction` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.summary_role` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.summary_username` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.title` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.username` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.username_hint` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.username_invalid` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.username_placeholder` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `onboarding.username_taken` | onboarding | — | templates/register.html; register_scripts.js; run.py registration endpoints |
| `common.cancel` | shell | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `common.error` | shell | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `common.offline` | shell | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `common.ok` | shell | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `entry.armed` | shell | — | templates/login.html; run.py:index() |
| `entry.gate` | shell | — | templates/login.html; run.py:index() |
| `entry.secure` | shell | — | templates/login.html; run.py:index() |
| `entry.signal` | shell | — | templates/login.html; run.py:index() |
| `entry.standby` | shell | — | templates/login.html; run.py:index() |
| `entry.status` | shell | — | templates/login.html; run.py:index() |
| `files.account` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.accuracy` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.amount` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.back` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.category` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.checkpoints` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.choose_highlighted` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.collected` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.complete` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.confidence` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.directory_error` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.directory_failed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.disk` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.disk_heading` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.document` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.document_failed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.document_loading` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.done` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.duration` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.empty` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.end` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.event` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.file` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.about` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.atm` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.audio` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.camera` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.credentials` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.device` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.documents` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.download` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.financial` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.ghostlab` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.gps` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.market` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.network` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.personal` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.pictures` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.projects` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.social-media` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.system` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.tips-tricks` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.tools` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folder.vehicle` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.folders` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.fragment` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.installed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.inventory_missing` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.load_failed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.loading` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.map_action` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.market` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.missing` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.no` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.no_checkpoints` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.no_records` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.no_resources` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.no_resources_ascii` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.no_upper` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.none` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.open_document` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.open_failed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.opening` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation_type` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.atm_log_extraction` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.audio_interference` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.camera_shutdown` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.camera_stream` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.device_tracking` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.generic_trace` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.persistent_sniffer` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.vehicle_ecu` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.vehicle_tracking` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.operation.wifi_scanner` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.package_resources` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.player_material` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.project_failed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.public` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.quality` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.quality_ascii` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.records` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.resource_heading` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.resources` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.retry` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.risk` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.sellable` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.session_changed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.simulated_open` | shell | name: string | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.size` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.soft_limit` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.source` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.start` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.state` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.sync` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.tier` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.time` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.title` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.type` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.uninstall` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.uninstall_failed` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.uninstallation` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.uninstalled` | shell | name: string | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.use` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.value` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.withdraw` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `files.yes` | shell | — | terminal.js:createFileManager()/runFile()/openFolderInManager() |
| `profile.apps` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.area` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.calculating` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.clan` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.clusters` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.coins` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.conflict` | shell | names: string | terminal.js:createProfile(); /api/profile/security |
| `profile.density` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.density_value` | shell | multiplier: string, spans: string | terminal.js:createProfile(); /api/profile/security |
| `profile.effective` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.level` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.loading` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.missing` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.next` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.no_threshold` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.none` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.off` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.on` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.points` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.position` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.profession` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.range` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.respect` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.save_failed` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.saved` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.saving` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security_empty` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.activity_monitor` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.background_injection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.browser_history_log` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.browser_protection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.exploit_protection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.file_indexing` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.file_visibility` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.firewall` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.firewall_core` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.heap_protection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.kernel_guard` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.log_guardian` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.log_integrity` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.memory_guard` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.memory_lock` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.network_anomaly_detection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.os_hardening` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.player_tracking` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.process_monitor` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.scan_detection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.spoofing_protection` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.stealth_mode` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.storage_integrity` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.system_integrity_check` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.system_visibility` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.unencrypted_access` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.vpn_blocker` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.security.vpn_enabled` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.sync` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.territory` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `profile.title` | shell | — | terminal.js:createProfile(); /api/profile/security |
| `session.code` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.denied` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.expired` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.inactive` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.instructions` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.login` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.profile_missing` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.profile_recovery` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.renew` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.replaced` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.replaced_login` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.signed_out` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.stale` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.stopped` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `session.title` | shell | — | session_generation_blocked.html; run.py recovery; login.html |
| `settings.error.current_password` | shell | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.error.image` | shell | index: number | terminal.js:createSettings(); run.py settings endpoints |
| `settings.error.map` | shell | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.error.no_changes` | shell | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.error.unauthorized` | shell | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.error.wallpaper` | shell | — | terminal.js:createSettings(); run.py settings endpoints |
| `settings.image` | shell | number: number | terminal.js:createSettings(); run.py settings endpoints |
| `shell.boot.emergency` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.failed` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.index` | shell | count: number | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.profile` | shell | name: string | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.ready` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.restore` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.toolbar` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.wait` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.boot.wake` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.checking` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.loading` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.logout` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.next_window` | shell | name: string | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.no_windows` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.restart` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.slow` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.switch_window` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.system_menu` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.target` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.target_captured` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.target_check` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.target_none` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.target_refresh` | shell | name: string | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `shell.window` | shell | — | terminal.js desktop/menu/taskbar/window controls/boot; ghost_i18n_frame.js |
| `terminal.ambiguous` | shell | ids: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.answer` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.app_missing` | shell | id: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.apps` | shell | entries: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.cancelled` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.close` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.completed` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.coordinates` | shell | command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.coordinates_invalid` | shell | command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.coordinates_range` | shell | command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.cwd` | shell | path: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.delete_admin` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.delete_login` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.delete_missing` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.delete_name` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.delete_own` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.delete_prompt` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.deleted` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.briefing` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.installed` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.launcher` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.motd` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.notes` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.readme` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.document.world` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.focus` | shell | position: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.focus_bad` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.focus_failed` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_accuracy` | shell | accuracy: number | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_current` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_denied` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_failed` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_https` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_invalid` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_timeout` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_unavailable` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_unsupported` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.geo_wait` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.ghostlab_missing` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.help` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.is_dir` | shell | path: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.launch` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.locked` | shell | command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.logout` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.ls_missing` | shell | path: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.missing_operand` | shell | command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.no_apps` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.no_dir` | shell | path: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.no_file` | shell | path: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.offline` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.open` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.parse` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_bought` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_buy` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_cancelled` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_confirm` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_details` | shell | price: number | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_empty` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_exact` | shell | query: string, suggestions: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_failed` | shell | status: number | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_installed` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_installer` | shell | item: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_list` | shell | count: number, entries: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_no_match` | shell | query: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_offline` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_purchase` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_rejected` | shell | details: string, reason: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_travel` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_travel_details` | shell | price: number | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_uncertain` | shell | reason: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.pkg_usage` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.rights` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.scan` | shell | count: number | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.script` | shell | index: number, total: number, command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.status` | shell | name: string, host: string, coins: string, used: string, capacity: string, apps: string, files: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport` | shell | position: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_bad` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_cancelled` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_confirm` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_details` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_done` | shell | name: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_rejected` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.teleport_title` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.unknown` | shell | command: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.usage` | shell | syntax: string | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.wait_location` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `terminal.welcome` | shell | — | terminals/commands.py; terminal.js:createTerminal()/handleTerminalPkgCommand(); /command |
| `wallet.accept` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.amount` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.balance` | shell | amount: string | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.balance_label` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.balance_loading` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.clear` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.empty` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.error.idempotency_conflict` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.error.insufficient_hc` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.error.wallet_not_initialized` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.error.wallet_write_rejected` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.event_other` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.event.wallet.seed` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.event.wallet.technical_transfer.incoming` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.event.wallet.technical_transfer.outgoing` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.event.wallet.transfer.incoming` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.event.wallet.transfer.outgoing` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.history` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.history_loading` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.invalid_request` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.load_failed` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.note` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.offline` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.optional` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.positive` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.received` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.recipient` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.recipient_required` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.rejected` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.reserved` | shell | reserved: string, available: string | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.sending` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.sent` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.subtitle` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.success` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
| `wallet.sync` | shell | — | terminal.js wallet renderer; run.py wallet_error_response() |
