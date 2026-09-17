# 142.1 — kontrakt scanu i wyłączenia kamer

Aktualny status: **ZAMKNIĘTY / PASS — ponowny odbiór autora 17 IX 2026**.
Autor potwierdził prawidłowe menu kamer, możliwość wyłączenia tylko raz podczas
trwania operacji oraz toast informujący o trwającej operacji przy ponowieniu.
Podsumował odbiór „mamy pass”, a następnie osobno potwierdził poprawne działanie
kropki celu na belce. Ten punkt ma zarówno potwierdzenie automatyczne, jak i ręczne.
Poniższe wpisy o cofnięciu PASS i oczekiwaniu na odbiór stanowią historię napraw.
Po wcześniejszej poprawce autor nadal zgłosił duplikację, brak kropki i złe menu.
Obecna paczka rozszerza DOM capture binding na oznaczone markery i odtworzone
ikony, zapisuje exploit dot wraz z operacją oraz deduplikuje także starszego
writera operacji i równoległe okna kamery. Cache JS: `camera-contract-142-1-race-2`.
Walidacja lokalna: 37 różnych testów Python i 4 skrypty JS PASS.

Odbiór tej paczki po deployu: świeży scan → oznaczenie → wyłączenie i kropka
exploit na belce → szybkie ponowienia mapa/pulpit/terminal (jedna operacja,
niezmieniony timer, jedno okno na tę kamerę) → kolejny scan i odświeżenie mapy.
Sprawdzić menu kilku odległych i sąsiadujących kamer po oznaczeniu oraz po
odświeżeniu: identyfikator celu ma odpowiadać klikniętej ikonie, nie tooltipowi.
Istniejące duplikaty nie są automatycznie kasowane; na test użyć kamery bez
aktywnej operacji albo wcześniej anulować stare operacje testowe.

Zakres: stabilna tożsamość kamery, dowód scanu po stronie backendu,
uprawnienie aplikacji i trwałe wykonanie shutdown. Nie zmienia współczynników
inicjacji/eskalacji, kar ani publikacji — następne etapy sprintu 142.

## Kontrakt

| Przejście | Źródło / zapis | Autoryzacja i recovery |
|---|---|---|
| Scan → kamera | Deterministyczne `camera_id`, `parent_target_id`, `target_type=camera`; generowane kamery mają stałą pozycję i liczbę dla danego celu | Kolejny scan nie losuje nowej tożsamości |
| Kamera → obserwacja | `response_camera_observations`, klucz gracz/scan/kamera, TTL zgodny ze scanem | Scan innego gracza, nieznane ID i wygasły dowód odrzucane; nowy scan nie usuwa wcześniejszego ważnego dowodu |
| Wybór aplikacji | Wąski odczyt `player_apps`, maks. 64 pasujące aplikacje | Wymagana deklaracja `camera_shutdown`; ograniczenia typu celu i operacji respektowane; brak fallbacku do zwykłego exploita |
| Shutdown | Backend wybiera współrzędne zapisanej kamery, sprawdza pozycję i zasięg, terytorium, aktualną projekcję uprawnień | Recheck pozycji, integralności/uprawnień, aplikacji i terytorium przed commit; obowiązuje globalna bramka sesji |
| Commit | Jedna transakcja: `player_operations`, `operation_events`, `player_launch_entries`, delta `map.operations_changed` | Stabilny receipt; błąd zapisu launchera wycofuje całość; kolejny scan nie przedłuża aktywnej operacji |
| Potwierdzenie aplikacji | `/gonna-win` odczytuje zapisany receipt należący do gracza i aplikacji | Nie wykonuje ponownie skutku i nie modyfikuje innego aktualnie zaznaczonego celu |
| Mapa / powrót | Istniejący magazyn i cykl operacji, delta odświeża otwarte mapy, recovery mapy odczytuje operacje | 15 minut, istniejące anulowanie/expiry; dowód kamery skopiowany do operacji przetrwa TTL obserwacji |

Kamera jest samodzielnym celem akcji mapowej: wymagany jest ważny własny scan,
zasięg i uprawniona aplikacja. Dostęp PvP do innego gracza nie stanowi uprawnienia
do tej akcji. Zakres wyłączenia jest obecnie przypisany do właściciela operacji;
publiczny wpływ/ochrona innych graczy nie jest dodawany w tej paczce.
Do budowy operacji używany jest istniejący builder, w tym risk meter i aktywne
reguły GhostNetwork. Nie wprowadzamy alternatywnego modelu obliczania ryzyka.

## Koszt i ograniczenia

Brak pełnego odczytu/zapisu profilu w ścieżce shutdown i potwierdzenia.
Test z profilem 35 MiB kontroluje `profile_full_read`, `profile_full_write`
i `profile_bytes` = 0. Maksymalnie 512 markerów scanu, 64 aplikacje do wyboru,
32 aktywne operacje przed utworzeniem nowej. Cleanup usuwa najwyżej 512
wygasłych obserwacji na zapis scanu. Dowód wyłączenia pozostaje w operacji.
Kontrola terytorium ponownie używa istniejącej ścieżki ograniczonej do 1000
obszarów; nie jest indeksem przestrzennym. Produkcyjnego p95 nie mierzono.
Cały istniejący endpoint scanu nie został w tej paczce przeniesiony na projekcje.

## Testy

Wynik lokalny 16 IX 2026: 44 testy Python PASS (43 w regresji i jeden dodatkowy
test równoległych ponowień). Trzy skrypty JS PASS: delta kamer, cancel dispatch
i renderer centrum operacji. Składnia `terminal.js` poprawna.

Uruchamiać wyłącznie runnerem z izolowanym cwd/bazą:

```powershell
python -B tools/run_isolated_tests.py test_camera_shutdown_contract test_player_launcher_hot_path test_camera_incident_audit test_operation_risk_meter test_operation_control
node tests/js/test_camera_operation_delta.js
```

Sprawdzamy tożsamość i współrzędne, TTL/własność, aplikację, zasięg,
zmianę stanu pomiędzy check/commit, replay, anulowanie i rollback.
Test JS wykonuje odbiór delty, deduplikację i recovery. Testy audytowe ryzyka
nadal potwierdzają brak nowego wpływu kamer na publiczny heat — naprawa 142.2.
Stare testy anulowania dopasowane do istniejących canonical store'ów zamiast
podstawiania nieużywanej już mutacji pełnego profilu.

## Wdrożenie i odbiór ręczny

1. Standardowy backup przed wdrożeniem, pobranie zmian i restart `chaos` po nazwie.
   `init_db` dodaje pustą tabelę obserwacji i indeks; nie przepisuje profili.
   Nie uruchamiać ponownie migracji projekcji wyłącznie dla tej zmiany.
2. Otworzyć ponownie pulpit i wykonać **nowy scan** — stary marker bez ID/dowodu
   nie otrzymuje automatycznej autoryzacji.
3. Wybrać kamerę w zasięgu oraz uprawnione narzędzie. Potwierdzić wynik aplikacji,
   jedną operację i jej timer na mapie.
4. Ponowić akcję i scan: brak drugiej aktywnej operacji oraz przedłużenia czasu.
5. Odświeżyć pulpit/mapę: operacja jest nadal widoczna. Anulować ją w centrum
   operacji i sprawdzić koniec aktywnego wyłączenia.

Odbiór gameplayu: **PASS COFNIĘTY — 17 IX 2026** na prośbę autora po zauważeniu
problemu. 142.1 ponownie otwarty; oczekuje ponownego odbioru poprawki.
Wcześniejsze wyniki testów automatycznych pozostają historycznym
potwierdzeniem sprawdzonych scenariuszy, nie zamykają odbioru gameplayu.
Przejście do 142.2 wstrzymane do wyjaśnienia problemu.

### Poprawka transportu danych kamery — 17 IX

Żądanie autora zawierało `camera_id=null` i `scan_id=null`. Potwierdzono utratę
danych w oznaczaniu celu, wyborze aktywnego celu i serializerze snapshotu mapy.
Zachowano camera_id/scan_id/parent_target_id w tych przejściach oraz markerze
aktywnego celu renderowanym przez backend. Autoryzacja nadal odczytuje dowód
scanu z bazy; skopiowane metadane same nie uprawniają do shutdown.
Test integracyjny scan store → mark_target → target-snapshot → shutdown PASS.
22 testy Python i 2 skrypty JS PASS. Test źródła mapy korzysta ze ścieżki
względem pliku testu, aby działał z izolowanym cwd.
Po deployu wykonać nowy scan, ponownie oznaczyć kamerę, odświeżyć mapę i użyć
wyłączenia z jej menu. Nie uzupełniamy starych markerów zgadywanym ID.
W samej poprawce transportu starsza ścieżka pulpitu nie była ujednolicona;
uzupełniono to w poprawce deduplikacji poniżej.

### Wspólna deduplikacja mapy, pulpitu i terminala — 17 IX

Autor potwierdził uruchamianie, ale zgłosił drugą operację przy ponowieniu.
Pulpit/terminal tworzyły operację starszą ścieżką, z innym kluczem celu.
Teraz `/gonna-win` kieruje narzędzie wyłączające kamerę na kanonicznym celu
kamery do tej samej autoryzacji/transakcji co mapa, przed odczytem profilu.
Sprawdza też oczekiwany cel oraz jego niezmienność przy commit. Uruchomienie
z pulpitu nie dodaje kolejnego startu do kolejki launchera.
Deduplikacja obejmuje ID kamery, ID w snapshotach i starsze operacje dla
dokładnie tej samej pozycji. Uwzględnia status i expires_at; nie zależy od
wybranej aplikacji ani kolejnego scanu. Istniejące duplikaty nie są usuwane.
Stary marker bez ważnego dowodu jest odrzucany z komunikatem o nowym scanie.

Weryfikacja: 15 testów kamer PASS oraz 7 testów launchera PASS w regresji.
Nowe scenariusze: desktop → mapa → nowy scan → terminal; mapa → inna aplikacja
z pulpitu; wcześniejsza operacja bez camera_id; stary scan z pulpitu.
Po deployu wykonać świeży scan i oznaczyć kamerę bez aktywnej operacji (lub
wcześniej anulować stare operacje testowe). Uruchomić raz, zapisać timer,
ponowić z mapy/pulpitu/terminala i po kolejnym scanie. Oczekiwane: jedna
operacja, ten sam expires_at, bez resetu timera. 142.1 nadal otwarty do odbioru.
