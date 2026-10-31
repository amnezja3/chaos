# Camera Street View — raport pierwszej paczki lokalnej 165.1

31.10.2026. Baza HEAD `3556abdcb9603110271e0ea7563fbea4f590ae63`, zmiany lokalne,
bez commit/push/VPS. [Kontrakt operatora](../plans/camera_street_view_operator_contract_2026_10_31.md).
[Wdrożenie i rollback](../runbooks/camera_street_view_package_165_1.md).

## Co obejmuje kod

- camera_stream korzysta z istniejącej budowy operacji, runtime/ryzyka,
  finalizerów plików i mocy. Usunięto nadpisanie czasu 1800 s. Termin i postęp
  są odczytywane z kanonicznej operacji, także po późniejszym przyspieszeniu.
- Potwierdzony zapis aktywatora jest konieczny. Sam frontendowy upływ czasu
  nie daje dostępu. Ręczne zamknięcie zapisuje trwałe zużycie; stare `reopen`
  odrzucane. Przy błędzie zapisu zamknięcia okno pozostaje z komunikatem retry.
- Kolejny sukces po zamknięciu tworzy nowy download, receipt i instancję.
  Generowany jest nowy wektor, nawet przy ponownym użyciu tego samego zdjęcia.
  Odzyskanie aktywnej instancji zachowuje zdjęcie i tor; brak timera oglądania.
- Kamery świata sprawdzane przez CameraContractStore/obserwację skanu,
  kanoniczny cel, pozycję i zasięg. Legacy wyjątek zostaje w ograniczonym pilocie.
  Zgodne nowe i starsze aplikacje używają wspólnej ścieżki przez kontrakt.
- Materiały współdzielone przez archiwum; brak uprawnień wynikających z samego
  cache. Adapter, selekcja kierunku/odległości, WebP, limity, lease/fencing,
  negatywny cache, retencja, tombstones, GC i addytywny backup/restore.
- Ukończone pobranie otwiera okno również przy oczekiwaniu na fotografię.
  Materiał może pojawić się później bez odtwarzania DOM. Wycofanie blokuje media
  i przełącza istniejący podgląd na NO SIGNAL.
- Panel admina pokazuje ograniczoną listę archiwów, stany, limity i obecność
  sekretu; operacje wycofania/GC/backup są w CLI. Publiczne źródła PL/EN.
  Konfiguracja web i osobnego workera domyślnie OFF.

## Dowody lokalne

Windows, Python 3.11/.venv, Pillow 12.3.0, Playwright MCP. Gra na izolowanej
kopii `instance/cvn-gameplay-164`, lokalny serwer 9001; backup źródłowy nietknięty.

| Zestaw | Wynik |
| --- | --- |
| `test_camera_visual_gameplay.py` | 22 PASS, ostatni pełny przebieg 131.093 s |
| `test_camera_archive.py` | 10 PASS: adapter na fixtures, selekcja, budżet, SSRF/redirect, optymalizacja, wycofanie, backup/restore, fencing, retry |
| `test_camera_shutdown_contract.py` | 20 PASS |
| `test_camera_exposure.py` | 8 PASS — wyłączenie kamer nadal zmienia próg incydentu, inne składowe ryzyka bez zmian |
| `test_camera_incident_audit.py` | 3 PASS |
| JS camera window dedupe / target transport / operation delta | 3 PASS |
| Playwright `camera_visual_gameplay_164_0.js` | 31 kontroli PASS: normalne okno, ruch, resize/mobile, utrwalenie, dwie karty, zużycie, odmowa reopen |
| Playwright resize i reconnect | PASS; ta sama instancja, brak ponownego pobrania zdjęcia po odzyskaniu |
| Playwright `camera_street_view_material.js` | PASS; kontrolowana fixture metadanych na realnym uprawnieniu, późny obraz bez zmiany DOM, atrybucja, anulowanie zewnętrznej nawigacji |
| Publiczne `/camera-sources` | Playwright PL/EN, mobile PASS; wyłączone z blokad gameplayu jak strony prawne |
| Zamknięcie przy błędzie sieci / ponowne logowanie | potwierdzone w Playwright; błąd nie usuwa okna, skuteczne zamknięcie przetrwało logout/login |

Testy czasów wykorzystują kontrolowany zegar i prawdziwy realizer mocy,
bez skracania produkcyjnych wartości. Osobno 300/1800 s, przyspieszenie przy
tworzeniu i w trakcie operacji, odzyskanie instancji po siedmiu dniach (backend).
World cases obejmują kamery przy sklepie, bankomacie i innym POI.
Nowy browser grant przygotowano przez kanoniczny serwis i runtime na lokalnej
kopii z zegarem cofniętym o pełny czas operacji. Nie mierzono 30 minut zegarem
ściennym i nie przywracano zużytych grantów.

Celowe błędy w testach: 503 podczas reconnect, 409 przy próbie reopen i zerwane
żądanie close. Nie są awariami zwykłego show. Poprawiono również testową kolizję
nawigacji po logout (session bridge sam przechodzi do ekranu logowania).
Panel admina: render/autoryzacja sprawdzone backendowo; próba Playwright kontem
main poprawnie dała 403. Brak hasła admina w izolowanym środowisku — nie przypisujemy
panelowi pełnego browser PASS.

## Hot path i bezpieczeństwo

Test z profilem ≥35 MB wymusza `profile_full_read=0`, `profile_full_write=0`,
`profile_bytes=0`; wywołania pełnego profilu są blokowane w testach.
Runtime korzysta z target/position/capability/inventory/operation stores.
Schema init tylko przy inicjalizacji bazy/migracji. Snapshot ograniczony do 64
sesji, aktywne przed zużytymi. To pakiet kontrolowanego pilota, nie dowód skali
masowego rollout. Przy rollout konieczna weryfikacja limitu aktywnych okien.
HTTP i obróbka zdjęć są poza writer lock i poza web request. Krótkie transakcje
rezerwują budżet/lease i publikują manifest. Brak nowych pełnych profili.

Wszystkie żądania adaptera w testach zastąpił transport fixture. Nie wykonano
żadnego wywołania prawdziwego Mapillary API. Czytano publiczną
[dokumentację oficjalnego SDK](https://mapillary.github.io/mapillary-python-sdk/docs/mapillary.config.api/mapillary.config.api.entities/)
dla pól miniatur, geometrii i autora. Brak fallbacku do oryginałów; dokładne
hosty CDN pozostają konfiguracją kontrolowanego pilota, domyślnie lista pusta.

## Status dostarczenia

Kod lokalny i procedura przygotowane do jednej paczki z flagami OFF.
Paczka oznacza zintegrowany zakres w repozytorium, przygotowany do standardowego
commit/push i deploymentu Git. [Dokładny wykaz plików](camera_street_view_165_1_git_scope.md).
Korekta workflow: przed usunięciem dodatkowego ZIP zweryfikowano CRC i zgodność
wszystkich 99 plików bajt po bajcie z repo oraz SHA-256. Manifest w ZIP był
identyczny z zewnętrznym. Brak unikalnego kodu lub dowodów testowych w archiwum.
Usunięto wyłącznie ZIP, jego manifest/sumę i zbędny builder; zachowano źródła,
testy, zrzuty, raporty i niezmienny wzorzec zaakceptowanej prezentacji.
Sprawdzono status/diff oraz pliki nowe; dotychczasowe wyniki testów powyżej
pozostają dowodami wykonanych przebiegów. Nie ponawiano testów przy tej korekcie
dokumentacji i dystrybucji. Nie zmieniono działającej implementacji.
Nie jest to akceptacja API, wdrożenia, praw do zdjęć ani publicznego rollout.
Otwarte bramki 166: L01/L02, retencja i hosty próbki, rzeczywisty API contract,
limity/awarie dostawcy, wydajność VPS oraz zainstalowana PWA. Nie włączono
PLAYER_UPLOAD, Ghost Lab Camera Creator ani fotografii graczy.

Zaakceptowany wzorzec: 28 plików w
`doc/prototypes/camera_view/accepted_164_0_2026_10_31`, SHA-256. Rozwijany kod
jest oddzielony od tego snapshotu. Plik operatora `v164_0/preview.css` nie był
edytowany i nie jest częścią paczki implementacyjnej.
