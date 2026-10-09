# Sprint 154 — rejestr kluczy i glosariusz

Stan: rejestr aktualnego pakietu. **2833 kluczy PL/EN**, 13 domen,
wersja pakietu `154.7.0`. Rejestr generuje
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
Fundament i18n: [raport 153](sprint_153_acceptance.md). Rejestr nie oznacza
pełnego odbioru sprintu 154 ani potwierdzenia wdrożenia.

| Klucz | Domena | Parametry | Źródło / renderer |
| --- | --- | --- | --- |
| `common.no` | foundation | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `common.unavailable` | foundation | — | ghost_i18n.py; ghost_i18n.js — fallback |
| `common.yes` | foundation | — | ghost_i18n.py; ghost_i18n.js — fallback |
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
| `creator.objects.atms` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.objects.audio` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.objects.cameras` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.objects.cars` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.objects.general` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.objects.people` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.file_no` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.file_none` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.file_optional` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.file_required` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.file_yes` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.menu` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.purpose.purpose` | map_actions | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `map.action_name.atm_logs` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.audio_hack` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.camera_shutdown` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.camera_stream` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.car_hack` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.exploit` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.install_sniffer` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.mic_sniff` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.scan_hotspots` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.scan_ports` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.sniff` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.trace` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.trace_device` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action_name.trace_gps` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.atm_logs` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.audio_hack` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.camera_shutdown` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.camera_stream` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.car_hack` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.exploit` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.install_sniffer` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.mic_sniff` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.scan_hotspots` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.scan_ports` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.sniff` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.trace` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.trace_device` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.action.trace_gps` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.accepted` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.already_captured` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.choose` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.connection` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.cooldown` | map_actions | seconds: number | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.failed` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.foreign` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.invalid_tool` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.no_app` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.own_vulnerability` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.player_not_found` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.profile` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.target_blocked` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.target_changed` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.timeout` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.vulnerability_expired` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.launch.waiting` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.menu.aim` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.menu.mark` | map_actions | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.menu.report` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.menu.travel` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.action` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.action_unknown` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.choose` | map_actions | action: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.disk` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.files` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.note` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.starting` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.title` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.tool` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.picker.use` | map_actions | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `creator.editor.add_command` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.add_option` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.available` | creators | installed: number, available: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.back` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.buttons` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.checking` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.choose_icon` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.command` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.default_execute` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.default_failure` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.default_run` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.default_start` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.default_success` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.discard` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.discard_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.edit` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.effect` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.effect_disabled` | creators | level: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.effect_enabled` | creators | level: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.error` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.failure` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.generate` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.icon` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.installed` | creators | version: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.interface_title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.invalid_icon` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.legacy` | creators | version: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.legacy_effect` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.list` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.locked` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.logs` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.more` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.name` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.new` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.not_installed` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.option` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.outputs` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.power` | creators | power: number, cap: number, version: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.preview` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.price` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.projects` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.prompt` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.publish` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.published` | creators | version: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.reload` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.save` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.saved` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.steps` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.success` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.update` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.use_price` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.will_lock` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.editor.withdrawn` | creators | installed: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.creator_not_installed` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.creator_rollout_pending` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.mechanics_frozen` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.name_conflict` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.not_installed` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.not_logged_in` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.project_limit` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.project_not_found` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.project_not_migrated` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.projection_unavailable` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.publication_owner_conflict` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.request_conflict` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.request_too_large` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.revision_conflict` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.error.version_limit` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.action` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.action_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.action_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.add_button` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.add_level` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.add_list` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.add_option` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.add_step` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.affects` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.affects_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.app` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.back` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.button_label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.catalog_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.choice_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.command` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.conflict_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.conflicts` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.contract_help.affects` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.contract_help.disables` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.contract_help.interferes_with` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.contract_help.requires_off` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_option_groups.map_actions` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_option_groups.operation_types` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_option_groups.resource_types` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_option_groups.target_types` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.access` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.accounts` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.device` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.finance` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.location` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.media` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.creator_semantic_group_labels.world` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.custom` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.description_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.desktop` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.detect_example` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.detect_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.detect_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.detects` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.disable_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.disables` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.disk` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.effect` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.exploit.desktop.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.exploit.desktop.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.exploit.hybrid.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.exploit.hybrid.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.exploit.map.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.exploit.map.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.failure_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family_label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.exploit.boxTitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.exploit.desktopMapNote` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.exploit.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.exploit.mapNote` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.exploit.safetyText` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.scanner_recon.boxTitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.scanner_recon.desktopMapNote` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.scanner_recon.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.scanner_recon.mapNote` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.scanner_recon.safetyText` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.sniffer.boxTitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.sniffer.desktopMapNote` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.sniffer.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.sniffer.mapNote` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.family.sniffer.safetyText` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.filter_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.filtered` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.filtered_count` | creators | count: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.general` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.general_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.general_mode` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.hybrid` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.icon` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.information` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.information_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.interface` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.invalid_icon` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.invalid_name` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.json` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.launch_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.legacy_name_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.levels` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.levels_many` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.list` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.list_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.list_lines` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.logs` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.logs_lines` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.map` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.map_actions` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.map_error` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.mode` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.mode_action_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.mode_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.mode_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.name` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.name_error` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.name_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.0.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.0.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.0.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.0.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.0.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.1.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.1.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.1.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.1.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.1.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.2.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.2.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.2.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.2.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.2.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.3.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.3.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.3.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.3.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.3.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.4.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.4.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.4.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.4.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.4.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.5.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.5.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.5.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.5.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.5.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.6.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.6.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.6.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.6.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.6.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.7.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.7.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.7.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.7.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.7.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.8.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.8.educational_note` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.8.gameplay_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.8.subtitle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.narrative.8.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.next` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.none` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.not_selected` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.operation_error` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.operation_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.operations` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option_label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.atm_logs` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.audio_hack` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.camera_shutdown` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.camera_stream` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.car_hack` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.exploit` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.install_sniffer` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.scan_hotspots` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.scan_ports` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.sniff` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.trace` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.trace_device` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.map_actions.trace_gps` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.atm_log_extraction` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.audio_interference` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.camera_shutdown` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.camera_stream` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.device_tracking` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.generic_trace` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.microphone_sniffer` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.persistent_sniffer` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.vehicle_ecu` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.vehicle_tracking` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.operation_types.wifi_scanner` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.atm_dump` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.audio_transcript` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.call_history` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.camera_dump` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.credentials` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.device_logs` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.email_accounts` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.financial_records` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.gps_logs` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.hotspot_database` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.internal_recon_state` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.location_history` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.messenger_data` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.personal_records` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.vehicle_diagnostics` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.video_material` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.resource_types.wifi_networks` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.atm` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.camera` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.person` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.phone` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.pillar` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.player` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.poi` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.router` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.server` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.vehicle` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.option.target_types.venue` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.panel_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.policy_failed` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.presentation` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.price` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.price_lower` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.profile` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.progress_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.progress_lines` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.progress_title_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.publish` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.publish_failed` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.publish_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.published_file` | creators | file: string | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.publishing` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.quality` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.reliability` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.requires` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.requires_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.resource_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.result_failure` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.result_success` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.run_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.runtime` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.scanner.desktop.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.scanner.desktop.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.scanner.hybrid.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.scanner.hybrid.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.scanner.map.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.scanner.map.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.sniffer.desktop.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.sniffer.desktop.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.sniffer.hybrid.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.sniffer.hybrid.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.sniffer.map.description` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.sniffer.map.label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.start` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step_label` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.0` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.1` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.2` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.3` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.4` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.5` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.6` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.7` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.step.8` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.success_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.success_unicode_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.target` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.target_error` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.target_help` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.target_question` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.terminal_logs_hint` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.text` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.title` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.atm_tool` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.camera_tool` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.custom` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.exploit` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.exploit_suite` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.scanner` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.sniffer` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.tracker` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.type.vehicle_tool` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.unnamed` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.legacy.weight` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.action` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.choice` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.choice_contract` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.choice_id` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.choice_interface` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.command_fields` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.commands` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.commands_unique` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.configuration` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.contract` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.contract_version` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_assignments` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_boolean` | creators | key: string | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_duplicate` | creators | key: string | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_interface` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_length` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_range` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_syntax` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.effect_unknown` | creators | key: string | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.file_choice` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.file_required` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.file_unavailable` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.generator_fields` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.icon` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.identity` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.invalid` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.json` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.labels_count` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.legacy_steps` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.level` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.list` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.mechanics` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.name` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.option` | creators | index: number | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.option_fields` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.options` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.presentation` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.presentation_only` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.price` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.publish_fields` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.published_actions` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.request_id` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.required` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.risk_range` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.text` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `creator.validation.versioned_choice` | creators | — | creator_editor.js; creator_messages.py; creator_policy.py; creator_routes.py; terminal.js icon picker (sprint 154) |
| `map.actor.actions` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.add_friend` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.aimed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.chat` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.chat_blocked` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.chat_open` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.chat_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.clan` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.contact` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.contact_failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.contact_offline` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.contact_sent` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.disabled` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.enabled` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.enemy_clan` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.friend` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.friend_blocked` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.intruder` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.level` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.mark_failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.mark_target` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.marked` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.missing_id` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.module_unavailable` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.neutral` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.pending` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.position` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.position_missing` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.profession` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.profile` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.profile_action` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.relation` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.same_clan` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.self` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.self_profile` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.source` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.sources` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.target_blocked` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.target_offline` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.target_status` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.territories` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.transfer_blocked` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.transfer_hc` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.unavailable` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.username` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.actor.wallet_open` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.atm` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.atm_camera` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.atm_customer` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.bicycle_station` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.courier` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.customer` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.guest` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.npc.shop_camera` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.activate` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.active` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.city` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.continent` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.country` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.local` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.map` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.range` | map_workspace | range: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.scale` | map_workspace | scale: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.power.world` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.preset.all` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.preset.low` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.preset.open` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.preset.regular` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.preset.secure` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.aimed` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.already_captured` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.conflict_expired` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.connection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.connection_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.foreign` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.invalid_coordinates` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.marked` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.marked_coords` | map_workspace | lat: string, lng: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.missing_label` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.missing_target_data` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.not_logged_in` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.out_of_range` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.profile_not_found` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.projection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.protected` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.reached` | map_workspace | lat: string, lng: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.registered` | map_workspace | action: string, lat: string, lng: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.scanned` | map_workspace | count: number | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.scanner_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.target_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.territory_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.travel_range` | map_workspace | range: number | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.travel_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.upstream` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.result.vulnerability_expired` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.access_level` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.activity_monitor` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.anonymity_score` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.background_injection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.browser_history_log` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.browser_protection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.exploit_protection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.exploit_success_rate` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.file_indexing` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.file_visibility` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.firewall` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.firewall_core` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.heap_protection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.kernel_guard` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.log_guardian` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.log_integrity` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.memory_guard` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.memory_lock` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.network_anomaly_detection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.os_hardening` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.player_risk_level` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.player_tracking` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.process_monitor` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.risk_level` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.scan_detection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.spoofing_protection` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.stealth_mode` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.storage_integrity` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.system_compromise_level` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.system_integrity` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.system_integrity_check` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.system_visibility` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.traceability` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.unencrypted_access` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.vpn_blocker` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.security.vpn_enabled` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.coverage` | map_workspace | coverage: number, threshold: number | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.reported` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.swarm` | map_workspace | count: number | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.withdraw_failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.vulnerability.withdrawn` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandon` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandon_confirm` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandon_details` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandon_failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandon_prompt` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandon_title` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.abandoned` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.avatar` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.cancel` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.choose_tool` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.clear` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.corridor` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.decoy` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.delayed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.end` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.error` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.false_view` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.hack_error` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.history_empty` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.history_future` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.history_soon` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.masked` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.narrative` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.open_tools` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.operation` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.operation_target` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.operations` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.panel_resize` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.phantom` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.power_ended` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.predicted` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.refresh` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.replicated` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.revealed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.risk` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.safe` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.scan` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.scanning` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.secure` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.security_error` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.security_failed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.snapshot` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.stale_removed` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.start` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.target_linking` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.target_loading` | map_workspace | name: string | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.teleport` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.tools` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.travel` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.travel_far` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `map.workspace.withdraw` | map_workspace | — | templates/map_template.html menu; terminal.js map tool picker (sprint 154) |
| `radio.any` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.channel.blacknet.description` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.channel.blacknet.name` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.channel.ghost.description` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.channel.ghost.name` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.channels` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.choose` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.empty` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.filter` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.mixed` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.mute` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.neutral` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.next` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.no_track` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.pause` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.play` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.previous` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.program` | radio | language: string | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.autoplay_off` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.bad_schema` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.click_to_start` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.no_tracks` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.one_channel` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_boot` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_error` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_idle` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_loading` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_lost` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_online` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_paused` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_ready` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_search` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.status.signal_tuning` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.unknown` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.unmute` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `radio.volume` | radio | — | ghost_radio.js; radio_locale.py; /api/radio/channels; /api/radio/channel (sprint 154) |
| `apps.agi.accepted` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.accepted_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.completed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.cost` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.created` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.failed_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.heading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.medium` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.no_receipt` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.placeholder` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.processing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.processing_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.publishing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.queued` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.queued_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.ready` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.rejected` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.rejected_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.restore_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.result_link` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.result_ready` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.retry_status` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.same_receipt` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.sending` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.submit` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.template` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.topic` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.topic_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.topic_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.transport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.unconfirmed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.unconfirmed_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.agi.validating` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.action_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.archive_unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.bridge_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.bridge_unknown` | apps | action: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.cancel` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.cancelled` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.captured` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.decision` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.decision_details` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.down` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.exchange_open` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.exchange_sector` | apps | sector: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.execute` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.expired` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.informational` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.left` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.map_focus` | apps | target: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.map_unfocused` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.navigation` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.next` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.no_bridge` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.none` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.operation_blocked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.operation_focus` | apps | id: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.operation_open` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.operation_prompt` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.plex_open` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.plex_query` | apps | query: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.previous` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.radio_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.radio_unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.right` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.strength` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.strength_aria` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.suite_check` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.suite_focused` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.suite_install` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.suite_open` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.suite_open_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.suite_unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_cancelled` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_details` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_done` | apps | target: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_prompt` | apps | target: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.teleport_title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.thread_missing` | apps | peer: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.track_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.up` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.blacknet.valid` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.browser.refresh_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.files` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.ghost_exchange` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.googleplex` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.login` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.operations` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.other` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.performance` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.category.ui` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.dev_only` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.login_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.sending` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.sent` | apps | id: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.severity` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.severity.blocker` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.severity.high` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.severity.low` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.severity.medium` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.steps` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.submit` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.bugs.title_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.cluster_not_found` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.confirmation_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.invalid_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.invalid_preset` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.missing_action` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.missing_target_id` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.not_logged_in` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.profile_not_found` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.security_save_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.stale_owner` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.stale_version` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.target_not_found` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.target_unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.control.error.territory_control_not_installed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.add` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.add_contact` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.back` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.agi2108.meta` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.agi2108.preview` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.agi2108.subtitle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.agi2108.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.clan.preview` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.clan.subtitle` | apps | clan: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.clan.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.friends.meta` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.friends.preview` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.friends.subtitle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.friends.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.world.meta` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.world.preview` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.world.subtitle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channel.world.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.channels` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.compose` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.contact` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.direct` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.friends` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.new` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.new_small` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.nickname` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.pending` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.placeholder` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.private` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.remove` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.runtime_pending` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.send` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.send_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.soon` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.source` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.unknown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.unknown_contact` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.world_preview` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.world_source` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.cyberner.world_subtitle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.auth_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.average` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.background` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.earned_today` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.earned_total` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.file_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.file_unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.files` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.hc_today` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.history` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.history_accessible` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.history_empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.listed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.load_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.missing_mb` | apps | count: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.missing_records` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.offer_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.offer_ready` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.package` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.packages` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.pending` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.pending_data` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.request_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sale_completed` | apps | amount: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sale_duplicate` | apps | amount: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.atm` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.audio` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.camera` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.credentials` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.device` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.financial` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.gps` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.network` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.personal` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.unknown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sector.vehicle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sell_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sold` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.sold_today` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.status.collecting` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.status.trading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.atm` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.audio` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.camera` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.credentials` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.device` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.financial` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.gps` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.network` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.personal` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.unknown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.subtitle.vehicle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.transactions` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.transactions_count` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.exchange.volume` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.ability` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.all` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.archived` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.blocked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.clan` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.clan_caption` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.code` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.control` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.cycle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.cycle.active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.cycle.closed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.cycle.preparing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.cycle.stabilizing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.cycle.transmitting` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.details` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.discovered` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.discovered_count` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.distance` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.load_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.location.exact` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.location.hidden` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.location.territory_only` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.machine` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.map_disabled` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.map_part` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.no_map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.no_teleport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.owner` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.owner_caption` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.part` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.profession` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.public` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.refresh` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.choose` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.clan_metrics` | apps | nodes: number, territories: number, area: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.clans_all` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.clans_signal` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.closer` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.conflict` | apps | score: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.contract` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.no_ranking` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.player_metrics` | apps | rsp: number, nodes: number, territories: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.players_all` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.players_signal` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.registry.select` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.restart` | apps | transition: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.search` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.search_parts` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.snapshot_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.sort` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.stale` | apps | error: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.state` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.strategic` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.sync` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.sync_detail` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport_denied` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport_disabled` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport_done` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport_part` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.message` | apps | label: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.node` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.node_contested` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.territory` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.territory_contested` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.title_node` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.teleport.title_territory` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.territory` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.update` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.updated` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.blocked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.clan_own_active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.contained` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.contested` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.foreign_active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.foreign_blocked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.inactive` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.public` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.public_neutral` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.self_foreign_blocked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.self_own_active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.summary.active_foreign` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.summary.contained_hidden` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.summary.full` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.network.value.unknown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.back` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.cancel` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.cancel_group` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.cancel_warning` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.cancelled` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.cancelled_group` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.cancelling` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.clear` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.close` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.confirm` | apps | name: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.confirm_group` | apps | name: string, count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.distance` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.empty_group` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.empty_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.ended` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.atm` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.audio` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.camera` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.credentials` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.device` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.financial_records` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.gps` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.implant` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.network` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.other` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.recon` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.system` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.family.vehicle` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.group_warning` | apps | types: string, count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.groups` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.history` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.incident` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.incidents` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.invalid_request` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.load_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.login_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.no_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.not_active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.not_found` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.not_installed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.output` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.refresh` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.remaining` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.risk.critical` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.risk.high` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.risk.low` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.risk.medium` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.cancelled` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.completed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.created` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.expired` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.pending` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.resolved` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.state.running` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.summary` | apps | count: number, incidents: number, size: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.target` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.atm_log_extraction` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.audio_interference` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.camera_shutdown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.camera_stream` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.device_tracking` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.generic_trace` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.implant_timer` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.microphone_sniffer` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.persistent_sniffer` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.vehicle_ecu` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.vehicle_tracking` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.type.wifi_scanner` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.operations.warning` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.history` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.journey_date` | apps | date: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.locked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.mute` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.no_dates` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.ghostsystem_restart.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.ghostsystem_restart.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.machine_synchronization.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.machine_synchronization.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.network_lock.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.network_lock.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.results.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.results.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.signal_transmission.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.signal_transmission.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.world_consumption.description` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.phase.world_consumption.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.recovery` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.replaying` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.restart_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.signal.unmute` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandon` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandon_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandon.confirm` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandon.details` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandon.message` | apps | label: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandon.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandoned` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.abandoning` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.ability` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.alarm` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.alone` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.alone_help` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.attack` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.attacked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.back` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.bike` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.clan` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.close` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.cluster` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.cluster_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.cluster_name` | apps | id: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.cluster_teleport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.clusters` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.collision` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.contested` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.foreign` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.hidden` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.own` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.stored` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.unidentified` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.component.unknown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.conflicts` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.counts` | apps | nodes: number, pillars: number, inners: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.details` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.flag_changing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.flag_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.from_bike` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.inners` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.invalid_teleport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.load_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.loading_cluster` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.machine` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.neutral` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.no_flags` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.no_inners` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.no_pillars` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.no_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.open_map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.pillars` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.preset_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.preset_saved` | apps | preset: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.preset_saving` | apps | preset: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.profession` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.recalculated` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.refresh` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.security` | apps | percent: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.show_cluster` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.show_map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.sync` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.sync_app` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.teleport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.teleport_denied` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.territory.teleporting` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.active_target` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.aim` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.aim_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.aim_offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.aimed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.aiming` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.back` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.clan` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.friend` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.missing_player_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.missing_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.out_of_range` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.own_vulnerability` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.self` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.badge.unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.bike_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.bike_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.cancel` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.candidates` | apps | count: number | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.clear_scan` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.close` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.current` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.current_target` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.empty_sources` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.focus_active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.go_victims` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.install_required` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.invalid_teleport` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.load_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.load_offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.mark` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.mark_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.mark_first` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.mark_offline` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.mark_title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.marked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.marked_ready` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.marked_title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.marking` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.no_active` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.no_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.none` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.open_map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.range` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.reason.missing_player_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.reason.missing_position` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.reason.out_of_range` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.reason.own_vulnerability` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.refresh` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.danger` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.danger_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.no_distance` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.remote` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.remote_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.safe_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.unknown` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.warning` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.risk.warning_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_calibrate` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_denied` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_empty` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_failed` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_group` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_help` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_loading` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_result` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_signatures` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scan_validation` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.scanning` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.set_target` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.show` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.show_map` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.source.conflicts` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.source.intruders` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.source.marked` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.source.players` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.source.vulnerabilities` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.sync` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.sync_picker` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.target_missing` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleport_near` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleport.denied` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleport.details` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleport.done` | apps | label: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleport.message` | apps | label: string | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleport.title` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.teleporting` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `apps.victim.unavailable` | apps | — | terminal.js application renderers; run.py application endpoints (sprint 154) |
| `catalog.system.agi2108Console.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.agi2108Console.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.appforge.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.appforge.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.arsenalCleaner.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.arsenalCleaner.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_100.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_100.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_1000.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_1000.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_300.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_300.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_500.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bike_range_500.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.bttracer_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.buttonmaker.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.buttonmaker.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.0.logs.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.0.logs.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.0.logs.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.0.logs.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.1.logs.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.1.logs.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.levels.1.logs.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camdisabler_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.camstream_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.buttons.0.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.buttons.1.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.list.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.list.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.list.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.list.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.list.4` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.crypto_vault_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.data_corruptor_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.deep_sniff_r2.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.drivecrypt_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.financialSniffer.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.financialSniffer.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.friendKicker.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.friendKicker.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_lab.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_lab.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghost_ping_x3.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghostnetworkSuite.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ghostnetworkSuite.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.gpsprobe_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.0.logs.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.0.logs.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.0.logs.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.0.logs.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.1.logs.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.1.logs.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.levels.1.logs.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.injector_x_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.intruderKicker.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.intruderKicker.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.map_zoom_plus_1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.map_zoom_plus_1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.map_zoom_plus_2.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.map_zoom_plus_2.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.map_zoom_plus_3.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.map_zoom_plus_3.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.mem_overflow_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.micsniff_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.operationControl.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.operationControl.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.options.0.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.options.1.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.options.2.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.options.3.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.options.4.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.text` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.pencombo_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.phantom_vpn_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.levels.0.buttons.0.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.levels.0.buttons.1.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.levels.0.list.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.levels.0.list.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.levels.0.list.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.procmon_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_probe_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_100.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_100.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_1000.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_1000.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_300.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_300.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_500.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.scan_range_500.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.securityPanelProxy.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.securityPanelProxy.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.options.0.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.options.1.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.options.2.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.options.3.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.options.4.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.options.5.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.text` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.shadow_layer_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.buttons.0.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.buttons.1.label` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.list.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.list.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.list.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.list.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.stealth_browser_v2.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_blackvault.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_blackvault.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_data_vault.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_data_vault.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_encrypted_cluster.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_encrypted_cluster.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_ghost_vault_basic.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_ghost_vault_basic.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_ghost_vault_plus.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.storage_ghost_vault_plus.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.systemLogReader.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.systemLogReader.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.termcreator.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.termcreator.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.territoryControl.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.territoryControl.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_berlin.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_berlin.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_krakow.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_krakow.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_londyn.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_londyn.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_nowy_jork.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_nowy_jork.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_tokio.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_tokio.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_warszawa.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.ticket_warszawa.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.victimPicker.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.victimPicker.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.result_failure` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.result_success` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.steps.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.steps.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.steps.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.steps.3` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.levels.0.title` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.wifibreaker_v1.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.windowmaker.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.windowmaker.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.zeroday_hunter.description` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.zeroday_hunter.levels.0.logs.0` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.zeroday_hunter.levels.0.logs.1` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.zeroday_hunter.levels.0.logs.2` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `catalog.system.zeroday_hunter.name` | catalog | — | catalog_presentation.py; run.py code-owned products; terminal.js Googleplex (sprint 154) |
| `shop.all_categories` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.all_products` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.application` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.balance_required` | shop | price: number, balance: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.buy` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.buy_document` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.cancelled` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.bike_upgrade` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.documents` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.map` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.other` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.storage_upgrade` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.tools` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.category.travel_ticket` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.clan_only` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.confirm.buy` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.confirm.details` | shop | name: string, price: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.confirm.message` | shop | name: string | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.confirm.purchase` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.confirm.travel` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.confirm.travel_message` | shop | destination: string | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.document_ready` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.downloads` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.effect.bike_range_bonus` | shop | value: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.effect.map_zoom_bonus` | shop | value: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.effect.scan_range_bonus` | shop | value: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.effect.storage_capacity_bonus` | shop | value: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.effect.travel_city` | shop | city: string | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.empty` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.faction_required` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.failed` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.free` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.global` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.install` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.installation` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.installed` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.installing` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.level_required` | shop | level: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.load_failed` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.loading` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.no_description` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.no_funds` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.no_risk` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.not_found` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.offer_changed` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.offline` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.open_source` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.owned` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.price` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.products` | shop | count: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.purchased` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.authored` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.bad` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.change` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.current` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.empty` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.failed` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.happy` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.history` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.instant` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.loading` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.own` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.retry` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.travel_required` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.reaction.very_happy` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.recovery` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.requirements` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.respect_required` | shop | respect: number | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.results` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.search` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.search_blacknet` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.search_exchange` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.session_expired` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.soft_limit` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.audience` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.category` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.creator` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.data` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.effect` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.family` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.install` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.level` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.map` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.mode` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.open-source` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.ops` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.power` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.price-hint` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.product` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.quality` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.reliability` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.tier` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.spec.weight` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.components` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.document` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.download` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.finish` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.register` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.start` | shop | name: string | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.step.travel` | shop | name: string | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.travel` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.travel_ready` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.untrusted` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.validation` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.Advanced` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.Basic` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.bike_upgrade` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.camera_tool` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.creator` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.creators` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.desktop` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.Elite` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.hybrid` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.Legendary` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.map` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.map_upgrade` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.Pro` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.pro-system-lab` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.pro-system-tool` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.pro-system-tools` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.recon` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.scan_upgrade` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.scanner` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.storage` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.storage_upgrade` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.system_lab` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.tool` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.tracker` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.travel` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.value.travel_ticket` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `shop.withdrawn` | shop | — | terminal.js Googleplex/installer; run.py /install-app and catalog projections (sprint 154) |
| `lab.check.author_description` | lab | description: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.boolean` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.category` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.characters` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.cleaner` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.cleanup` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.contract` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.cooldown` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.coordinates` | lab | lat: string, lng: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.delete_warning` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.demonstration` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.detection` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.effect_steal` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.enum` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.fields` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.firmware` | lab | chance: string, disk: string, scan: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.firmware_limits` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.firmware_policy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.friend` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.groups` | lab | groups: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.icon` | lab | icon: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.include_status` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.latest` | lab | version: string, status: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.log_count` | lab | count: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.no_build` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.notes` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.number` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.overlay` | lab | name: string, pattern: string, sfx: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.policy` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.policy_value` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.presets` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.preview` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.project` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.project_create` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.protected` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.protected_archive` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.reaction_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.ready` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.restore` | lab | preset: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.retry` | lab | retries: string, timeout: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.rules` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.security` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.sfx` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.state` | lab | status: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.success` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.system_update` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.target_policy` | lab | value: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.template` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.text` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.travel` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.travel_changed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.travel_coordinates` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.travel_frame` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.travel_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.travel_map` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.type` | lab | field: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.valid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.visibility.clan` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.check.visibility.global` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.empty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.history` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.library` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_0.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_0.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_1.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_1.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_2.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_2.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_3.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.official_3.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_10` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_11` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_12` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_13` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_14` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_15` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_16` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_4` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_5` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_6` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_7` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_8` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.paragraph_9` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.project_pick` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research_message` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research_missing` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research_note` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research_pick` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research_status` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.apps.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.apps.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.apps.unlock_0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.apps.unlock_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.apps.unlock_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.apps.unlock_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.finance.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.finance.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.finance.unlock_0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.finance.unlock_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.finance.unlock_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.finance.unlock_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.intel.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.intel.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.intel.unlock_0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.intel.unlock_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.intel.unlock_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.intel.unlock_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.security.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.security.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.security.unlock_0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.security.unlock_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.security.unlock_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.security.unlock_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.social.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.social.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.social.unlock_0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.social.unlock_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.social.unlock_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.research.social.unlock_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.tooltip.Documentation` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.tooltip.Ghost_Exchange` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.tooltip.Projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.tooltip.Research` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.tooltip.Templates` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.docs.unlocks` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.artifact_mismatch` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.authentication_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.build_limit` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.build_stale` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.clan_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.creator_projection_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.custom_runtime_unsupported` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.destination_disabled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.document_build_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.document_disabled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.document_limit` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.document_not_found` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.document_not_owned` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.failed` | lab | code: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_build_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_cooldown` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_limits` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_not_installed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_pending` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_purchase_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.firmware_state_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.ghostlab_migration_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.ghostlab_not_installed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_blueprint` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_branding` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_destination` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_folder` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_icon` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_lease` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_payload` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_project` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_reaction` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_receipt` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_request` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.invalid_window` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.inventory_limit` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.inventory_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.not_logged_in` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.offer_changed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.project_limit` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.project_not_found` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.project_revision_conflict` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.publication_name_conflict` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.publication_owner_conflict` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.publication_withdrawn` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.published_project_retained` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.purchase_key_conflict` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.purchase_key_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.request_id_conflict` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.request_id_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.requirements_not_met` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.restart_pending` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.runtime_disabled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.scanner_busy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.scanner_inactive` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.scanner_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.template_creation_disabled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.template_publication_disabled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.ticket_build_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.ticket_not_found` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.ticket_runtime_disabled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.travel_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.unsaved_blueprint` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.unsaved_branding` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.error.wallet_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.allowed_switches` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.button_color` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.camera` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.city` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.conflict_matrix` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.contact_message` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.content` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.cooldown_minutes` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.country` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.denied_log` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.denied_text` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.detection_percent` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.disk_mb` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.empty_log` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.empty_text` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.error_log` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.error_text` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.extra_retries` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.extra_timeout` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.failure_message` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.frame_color` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.frame_id` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.include_created_at` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.include_status` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.include_type` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.installers` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.lat` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.lng` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.log_1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.log_2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.log_3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.log_4` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.log_limit` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.menu_name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.objects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.pattern_id` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.place_name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.preset` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.presets` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.protected_apps` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.recon` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.redaction_policy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.remove_tools_file` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.reward_note` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.rules` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.scan_m` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.sfx_id` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.start_log` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.start_text` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.steal_percent` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.success_log` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.success_message` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.success_percent` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.success_text` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.system` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.target_policy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.usage_policy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.victim_message` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.field.visibility` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.access` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.access_changed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.access_to` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.app` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.app_removed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.apps` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.artifact_changed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.balance` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.chance` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.complete` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.confirmed_display_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.contact` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.contact_kicked` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.contacts` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.cooldown` | lab | seconds: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.detected` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.detection` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.expired` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.expired_locked` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.family_cooldown` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.hidden` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.invalid_reply` | lab | status: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.no` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.no_logs` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.no_security` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.no_tools` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.not_installed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.refresh` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.removed_app` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.removed_contact` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.reopen` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.arsenal_cleaner.removed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.arsenal_cleaner.unchanged` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.financial` | lab | amount: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.friend_kicker.removed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.friend_kicker.unchanged` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.intruder_kicker` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.security_panel` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.result.system_logs` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.roll` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.security_conflicts` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.security_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.security_saved` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.security_saving` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.silent` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.starting` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.stolen` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.truncated` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.type` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.unchanged` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.unconfirmed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.unsupported` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.victim` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.victim_balance` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.pvp.yes` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.result.compiled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.result.created` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.result.deleted` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.result.published` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.result.saved` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.result.withdrawn` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.access_required` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.action_result` | lab | label: string, result: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.action_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.application` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.choice_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.choose` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.completed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.confirmed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.execute` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.failure` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.free` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.loading` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.offline` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.option` | lab | index: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.quote` | lab | amount: number, recipient: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.quote_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.read_logs` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.refresh` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.rejected` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.reopen` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.reserve_quote` | lab | amount: number, recipient: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.reserved` | lab | amount: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.run` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.security` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.started` | lab | id: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.success` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.target` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.target_changed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.update` | lab | version: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.used` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.versions` | lab | installed: number, available: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.runtime.wait` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.api_error` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.buy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.buy_confirm` | lab | price: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.buy_price` | lab | price: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.capacity` | lab | disk: number, scan: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.chance` | lab | chance: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.checking` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.clean` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.cleanup_confirm` | lab | count: number, size: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.cleanup_count` | lab | count: number, size: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.cleanup_result` | lab | count: number, size: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.cleanup_run` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.cleanup_scope` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.confirm` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.confirm_details` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.crash_description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.crash_safe` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.crash_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.current` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.current_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_audio` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_denied` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_empty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_error` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_result` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_selected` | lab | effect: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_stopped` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_success` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.demo_visual` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.denied` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.detection` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.duplicate` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.empty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_check` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_failure` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_retry` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_risk` | lab | disk: number, scan: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_success` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.firmware_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.flash` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.flash_action` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.flash_confirm` | lab | chance: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.flash_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.flashing` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.gains` | lab | disk: number, scan: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.gains_saved` | lab | disk: number, scan: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.image_prepare` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.last_attempt` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.limits` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.next` | lab | date: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.no_attempt` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.no_gains` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.paid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.paid_check` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.pending_first` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.planned` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.preparing` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.preset` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.preview_error` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.purchase_summary` | lab | price: number, chance: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.purchase_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.refresh` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.refresh_next` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.restart` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.restart_preparing` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.restart_ready` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.restore` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.restore_confirm` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.restoring` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.retry` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.run` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.saved` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_activating` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_active` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_close` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_refresh` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_stopped` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scanner_update` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.scope_changed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.security_choose` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.security_confirm` | lab | preset: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.security_level` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.security_ready` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.security_result` | lab | preset: string, count: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.security_run` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.stop` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.update` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.update_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.update_result` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.update_run` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.service.withdrawn` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.arsenal_cleaner.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.arsenal_cleaner.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.deep_scanner.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.deep_scanner.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.file_cleanup.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.file_cleanup.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.financial_sniffer.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.financial_sniffer.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.firmware_update.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.firmware_update.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.friend_kicker.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.friend_kicker.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.intruder_kicker.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.intruder_kicker.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.ptk_document.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.ptk_document.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.security_panel_proxy.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.security_panel_proxy.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.security_restore.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.security_restore.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.system_log_reader.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.system_log_reader.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.system_update.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.system_update.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.travel_ticket.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.template.travel_ticket.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.active` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.back_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.back_projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.brand` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.builds` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.cancel` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.category` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.change_name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.choose_template` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compile` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compile_dirty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compile_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compile_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compile_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compiled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compiler_offline` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.compiling` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.create` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.create_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.create_project` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.created` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.creating` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.danger` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.delete` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.delete_button` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.delete_confirm` | lab | name: string | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.delete_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.delete_select` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.delete_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.deleted` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.deleting` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.description` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.description_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.dirty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.dirty_open` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.document_content` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.document_editions` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.document_settings` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.document_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.documentation` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.draft_saved` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.edit` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.editor_offline` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.empty_projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.empty_projects_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.export` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.export_dirty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.export_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.export_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.export_none` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.export_offline` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.exporting` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.field_unsupported` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.frozen` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.10` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.4` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.5` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.6` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.7` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.8` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.future.9` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.hide` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.hide_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.icon` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.icon_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.idle` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.invalid_save` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.launch` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.launch.document` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.launch.own_system` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.launch.player_hack_access` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.launch.purchase_travel` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.loading_projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.loading_templates` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.markdown_content` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.markdown_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.name_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.name_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.new_project` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.no_builds` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.not_selected` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.official` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.onboarding_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.onboarding_hidden` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.open_project` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.open_project_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.open_select` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.policy` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.presentation` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.presentation_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.preview` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.preview_empty` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.preview_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price_default` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price_placeholder` | lab | amount: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price_ptk` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price_pvp` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.price_ticket` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.progress` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.project_name` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.project_templates` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.projects_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.projects_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.projects_loaded` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.projects_loading` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.projects_offline` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publication` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_button_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_invalid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_none` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_stale` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publish_to` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.published` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publisher_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publisher_offline` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.publishing` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.render` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.requirements` | lab | level: number, respect: number | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.retain` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.risk` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.0` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.1` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.2` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.3` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.4` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.5` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.6` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.7` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.roadmap.8` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.runtime_document` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.runtime_pvp` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.runtime_self` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.runtime_travel` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.runtime_unavailable` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.save` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.save_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.save_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.saved` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.saving` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.select_open` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.select_project` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.settings` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.standard` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.state` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.active` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.bundled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.compiled` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.current` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.done` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.draft` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.installed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.locked` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.planned` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.published` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.valid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.status.withdrawn` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.step_one` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.step_two` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.system_function` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tab` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tab.Documentation` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tab.Ghost_Exchange` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tab.Projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tab.Research` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tab.Templates` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.target` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.target.none` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.target.own_system` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.target.player` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.template` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.templates_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.ticket_publish` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.ticket_published` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.tier` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.update_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.valid` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.validate` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.validate_help` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.validating` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.version` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.withdraw` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.withdraw_confirm` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.withdraw_details` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.withdraw_failed` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.withdraw_prompt` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.withdraw_title` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.working` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
| `lab.ui.your_projects` | lab | — | ghostlab_registry.py; ghostlab_messages.py; ghostlab_routes.py; terminal.js GhostLab (sprint 154) |
