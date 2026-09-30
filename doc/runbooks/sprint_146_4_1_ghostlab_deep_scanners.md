# 146.4.1 — Deep Scanner: wdrożenie i odbiór

Status: **ZAMKNIĘTY / PASS autora**, 30 IX 2026, po poprawkach WAV,
wiadomości kolejnych skanów i powtarzania SFX do końca animacji.
Poniższy opis zachowuje zakres pierwszego deploymentu; rozszerza go
[146.4.2](sprint_146_4_2_ghostlab_scanner_effects.md).
Zakres: [146.4](../sprints/sprint_146_4_ghostlab_deep_scanners.md).

## Co trafia do wdrożenia

Template `deep_scanner`: własny branding i opis, nazwa przycisku do 12 znaków
Unicode po NFC (ikona osobno), ramki solid/double/dashed, cztery kolory ramki
i przycisku, presety oraz własne teksty dla startu, pustego wyniku, sukcesu,
błędu API i odmowy. Własny tekst jest tekstem, nigdy HTML. Kody 300/403 są
etykietami narracji; nie zastępują rzeczywistej odpowiedzi ani liczby obiektów.

Pierwszy etap udostępnia tylko działający `regular` oraz dwa rzeczywiste SFX:
`regular_sweep` i `regular_ping`. Generator własnych assetów:
`node tools/build_deepscanner_sfx.js`; pliki WAV są częścią pakietu.
Pozostałe cztery animacje oraz dalsze dopracowanie katalogu należą do 146.4.2.

Nakładka działa w otwartym oknie aplikacji, również kiedy mapa jest na wierzchu.
Zamknięcie aplikacji przywraca Skanuj i wyłącza efekty/SFX. Drugiej aplikacji
nie można aktywować równolegle. Ponowne uruchomienie aktywnej aplikacji pokazuje
jej istniejące okno. Nie powstaje osobny skaner ani narzędzie PvP.

## Wdrożenie

Po opublikowaniu zatwierdzonego pakietu na serwerze:

```bash
git pull
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 logs chaos --lines 80 --nostream
```

Konfiguracja PM2 zawiera `CHAOS_GHOSTLAB_SCANNER_RUNTIME_ENABLED=true`
i dotychczasowe `CHAOS_GHOSTLAB_RUNTIME_ACTORS=*`. Inicjalizacja bazy tworzy
tabelę aktywacji `ghostlab_scanner_leases`; nie wymaga przepisywania profili.
Odśwież pulpit i ponownie otwórz mapę, żeby załadować nowy JS/CSS/manifest audio.

Awaryjne wyłączenie: ustaw flagę scanner runtime na `false` i restartuj PM2
z `--update-env`. Zwykły Skanuj pozostaje dostępny. Kupione artefakty pozostają
w historii; wycofanie sprzedaży nie usuwa istniejących instalacji.

## Test skoordynowany — autor i kupujący

1. Bez aplikacji: sprawdź zwykłe Skanuj w pustym polu, terytorium i konflikcie.
2. Autor: utwórz Deep Scanner, ustaw nazwę przycisku, ikonę, kolory, ramkę,
   własny tekst startu/sukcesu i dźwięk. Podgląd animacji i odsłuch nie wykonują
   skanu. Validate → Save Draft → Compile → Publish.
3. Kupujący: kup/zainstaluj; sprawdź jedno obciążenie HC i wpływ do twórcy.
   Otwórz aplikację. Na mapie przycisk ma własną nazwę i ikonę we wszystkich
   trzech wejściach. Nie zmienia się mechanizm wykrywania ani zasięg firmware.
4. Skan: widać regular, tekst startu, wybrane akcenty i słychać wybrany SFX.
   Wynik ma narrację autora i prawdziwy systemowy wynik. Pusty wynik i odmowa
   zasięgu nie mogą być prezentowane jako sukces wykrycia.
5. Zamknij aplikację podczas skanu: efekty i SFX znikają, menu wraca do Skanuj.
   Odpowiedź już wysłanego żądania może dokończyć zwykły wynik; kolejne retry
   nie ruszają po utracie aktywacji. Zamknięcie samej mapy nie zamyka aplikacji.
6. Uruchom drugi produkt: blokada z nazwą aktywnego. Zamknij pierwszy i uruchom
   drugi. Sprawdź też dwie karty pulpitu; jedna aktywacja obowiązuje po stronie serwera.
7. Autor publikuje nowy build; kupujący pozostaje na starej wersji do jawnego
   „Aktualizuj bezpłatnie”. Aktualizacja nie pobiera HC i zmienia branding/politykę.
8. Odinstalowanie, wylogowanie/zmiana sesji oraz crash firmware usuwają nakładkę.
   Wymuszenie crasha nie jest konieczne podczas każdego odbioru — ścieżka objęta regresją firmware.
9. Mobile: menu mieści nazwę/ikonę, przycisk daje się dotknąć, okno działa według
   istniejącego układu Pro Tools. Sprawdź mute, głośność i pierwszy gest odblokowujący audio.
10. Admin: Deep Scanner oraz jego opublikowane wersje są widoczne w katalogu GLab.

## Polityka API i aktywacja

Domyślnie pozostają dwie próby endpointów z timeoutem 8 s (lub istniejącym
`CHAOS_OVERPASS_TIMEOUT_SECONDS`). Blueprint dopuszcza 0–3 dodatkowe próby
i 0–10 s do timeoutu każdej próby. Cały cykl ma budżet 110 s; nie zaczyna
kolejnej próby po jego wyczerpaniu. Retry dotyczą awarii połączenia/timeoutu
oraz HTTP 429/502/503/504, respektują Retry-After. HTTP 403 i poprawny pusty
wynik nie są ponawiane. Wszystkie próby to jedno wywołanie mechaniki skanu.

Serwer pobiera politykę z zainstalowanego, opublikowanego artefaktu. Parametry
przesłane ręcznie przez klienta jej nie nadpisują. Aktywacja jest związana
z kontem, generacją sesji, oknem i artefaktem; heartbeat co 10 s, wygaśnięcie
po 35 s. Zamknięcie wysyła zwolnienie. Przy utracie sieci/zabiciu przeglądarki
blokada drugiego okna może utrzymać się do wygaśnięcia. Odmowa heartbeatu
wyłącza nakładkę; odśwież aktywację w jej oknie.

Nie testuj retry przez obciążanie publicznych serwerów OSM. Testy automatyczne
podmieniają upstream i sprawdzają budżet, anulowanie, Retry-After, pusty wynik
i trwałą odmowę. Odsłuch oraz rzeczywisty wygląd wymagają odbioru w grze.

## Testy lokalne

```text
python -B tools/run_isolated_tests.py tests.test_ghostlab_scanner tests.test_ghostlab_alignment tests.test_poi_fetcher_geometry tests.test_poi_fetcher_latency_contract
python -B tools/run_isolated_tests.py tests.test_ghostlab_firmware tests.test_ghostlab_maintenance tests.test_ghostlab_publication tests.test_ghostlab_runtime tests.test_ghostlab_mutation_runtime
node tests/js/test_ghostlab_scanner.js
node tests/js/test_ghostlab_runtime.js
node tests/js/test_ghostlab_maintenance.js
node tests/js/test_ghostlab_firmware.js
node tests/js/test_game_sfx.js
node tests/js/test_app_uninstall_runtime.js
```

Testy runtime obejmują zakaz ciężkiego odczytu/zapisu profilu. Cały sprint 146.4
pozostaje otwarty do drugiego etapu i odbioru katalogu efektów.

Weryfikacja 28 IX 2026: testy backendu i sześć powyższych zestawów JS przeszły.
Zaktualizowano oczekiwaną liczbę templatek w testach katalogu/publikacji.
Sprawdzono także składnię zmienionego `mapAction` i obecność rzeczywistych WAV.
Nie przeprowadzono jeszcze wizualnego odbioru desktop/mobile ani odsłuchu w grze.
