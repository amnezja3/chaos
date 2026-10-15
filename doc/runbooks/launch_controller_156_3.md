# 156.3 — cichy start i powiązanie dokumentów

Stan: **GOTOWE LOKALNIE**, 15 X 2026; bez zmian na serwerze.
Instalacja PWA pozostaje w 156.4.

## Przepływ

`/launch` wyświetla publiczny ekran bez danych konta i formularza loginu.
GET `/api/session/status` sprawdza istniejący lifecycle bez aktywowania konta,
przedłużenia TTL lub migracji niekompletnej sesji legacy. Pozytywny wynik jest
wiązany z kartą przed POST `/api/session/bootstrap`. Bootstrap ponownie sprawdza
własność, termin i CSRF, następnie zwraca kontekst w pamięci klienta.

GET `/api/desktop-shell` z nagłówkiem generacji dostarcza istniejący dokument
`linux.html`. Klient montuje go jako dokument w tym samym oknie, zachowując
kolejność parsera/skryptów i DOMContentLoaded. W adresie pozostaje `/launch`.
Profil, boot snapshot i potwierdzenie restartu nadal obsługują istniejące endpointy;
status/bootstrap nie wydają nagród ani receiptów i nie tworzą nowego ownership.

Publiczny ekran i wszystkie odpowiedzi kontroli sesji mają no-store. Status
nie zawiera username, generacji ani nagłówków tożsamości. CSRF startu jest
oddzielnym HMAC związanym z SID/generacją, a nie credentialem API. W bootstrapie
wymagamy exact Origin, nagłówka klienta, CSRF i zgodnego bindingu z odczytu statusu.
Odpowiedzi chronione są sprawdzane ponownie przed zwrotem do klienta.

## Stara karta, mapa i admin

W `sessionStorage` znajduje się jedynie odseparowany domenowo HMAC porównawczy
`chaos-launch-binding-v1`; nie jest SID, generacją ani legacy query tokenem.
Nie można nim autoryzować API. Po unieważnieniu klient usuwa dane gracza, ale
zachowuje znacznik, żeby reload starej karty nie adoptował cookie nowego konta.
Dopiero jawny udany login/rejestracja lub logout usuwa ten znacznik.

Mapa/dev otwarte bez nagłówka otrzymują neutralny shell. Iframe pobiera kontekst
od swojego rodzica przez postMessage z kontrolą origin, source i nonce, po czym
pobiera chroniony dokument z nagłówkiem generacji. Stary rodzic nie daje ramce
nowego konta z cookie. Nieprawidłowy legacy query token nadal jest odrzucany.
Nowe linki admina i restart Show nie dopisują credentialu do URL.

Powrót widocznego dokumentu i pageshow z BFCache ponownie sprawdza status.
401/409 zatrzymuje kontekst; błąd transportu/5xx nie kasuje sesji. Retry startu
jest jawny, bez pętli automatycznych przekierowań. Przy niedostępnej pamięci
sesyjnej nowy launch pokazuje komunikat PL/EN zamiast osłabiać izolację kart.
Statyczne assety nie odczytują ownership i nie zapisują cookie.

## Flaga i kompatybilność

`CHAOS_LAUNCH_CONTROLLER_ENABLED` domyślnie **false**. Przy true:

- `/` prowadzi do `/launch`; `/?login=1` jawnie wyświetla login;
- poprawny login czyści znacznik tylko w tej karcie i przechodzi do `/launch`;
- rejestracja zachowuje dotychczasowy JSON, dodaje `launch_authenticated`;
- `/desktop`, `/map`, `/dev` bez nagłówka otwierają neutralny shell;
- dokumenty/API pozostają związane z generacją i epoch.

Wyłączenie flagi przywraca stare wejście i linki nowych dokumentów, ale `/launch`
oraz API bootstrapu pozostają dostępne. Nie usuwać ich podczas rollbacku.
Nie zmieniać tabel TTL ani nie przywracać unieważnionych sesji. Flaga startu
nie zastępuje flagi `CHAOS_PERSISTENT_SESSION_ENABLED` z 156.2.

## Weryfikacja lokalna

```text
python tools/run_isolated_tests.py test_launch_controller test_persistent_session test_persistent_session_flows test_session_generation_isolation test_session_generation_precommit test_ghostnetwork_client_restart test_ghost_i18n
node tests/js/test_launch_session_binding.js
node tests/js/test_session_generation_isolation.js
node tests/js/test_persistent_session_activity.js
python tools/session_156_launch_browser_smoke.py
```

Python uruchamia testy na tymczasowej bazie. Test UI wymaga pakietu Playwright
i zainstalowanego Chrome; używa lokalnego Flask na losowym porcie i tymczasowych
kont. Nie korzysta z produkcyjnych danych ani poświadczeń. Przeglądarkę zamyka
w bloku finally. Playwright MCP jest preferowany interaktywnie; w tej sesji nie
był dostępny, dlatego wykorzystano tę odtwarzalną ścieżkę lokalną.

Odbiór urządzeń, instalacji, magazynów iOS i restartu telefonu pozostaje w 156.5.
Emulacja mobilnego viewportu nie jest dowodem instalacji PWA. Instrukcję rollout
całego 156 z backupem i krokami operatorskimi dostarcza 156.6.

### Dowody z 15 X 2026

- Backend: **98/98 PASS**, 196,739 s. Lifecycle, status/bootstrap race, brak
  aktywacji legacy, CSRF/origin, stare dokumenty/mapa/dev, odmowa zwrotu danych
  po zmianie ownership, statyczne assety, precommit i restart/receipts Ghost Signal.
- Cztery zestawy Node PASS: binding i handshake ramek, izolacja generacji,
  activity/logout oraz rejestracja PL/EN.
- Chrome przez lokalny Playwright: desktop PL 1280×800 i mobile EN 390×844.
  Sprawdzono rzeczywisty język dokumentu, pulpit po preloaderze, ponowny start
  z tą samą generacją, brak żądania loginu przy ważnej sesji, mapę z kontekstem
  rodzica, zastąpienie konta i reload starej karty, ponowny jawny login formularzem.
- Symulowany brak transportu statusu: retry widoczne, brak loginu i cookie bez
  zmian; po przywróceniu połączenia pulpit otwiera się poprawnie.
- Brak pageerror i nieoczekiwanych błędów konsoli. Pięć komunikatów konsoli
  dotyczyło oczekiwanych odrzuceń podczas scenariusza zastępowania sesji.
  Browser zamknięty. Artefakty lokalne: `.playwright-mcp/launch-156-3*.log/png`.
- Wykryto przekroczenie wcześniejszego limitu zapytań boot snapshot. Usunięto
  niewykorzystywany odczyt security i współdzielono połączenie dla identity/
  capabilities. Istniejący test dla małego i 35 MB profilu przechodzi bez
  podnoszenia limitu; nadal brak pełnych odczytów/zapisów profilu.

Katalogi PL/EN: 156.3.0. Flaga domyślnie OFF. Brak wdrożenia, instalacji PWA
i pełnego PASS Sprintu 156.
