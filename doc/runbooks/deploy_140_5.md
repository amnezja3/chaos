# 140.5 — dane historyczne, wydajność i odbiór E2E

Status: wykonane testy PASS — potwierdzenie operatorskie 2026-09-12.
Zgodnie z doprecyzowaniem autora trigger i produkcyjny E2E z §4 czekają
na stylizację całego show. Szczegółowe raporty nie zostały załączone do
potwierdzenia. Zaakceptowany miks 140.4 pozostaje bez zmian.
Stylizacja: 140.stylization.1+. Wszystkie komendy wykonuj w `~/app/chaos`.
Przy błędzie zatrzymaj dany etap i zachowaj wynik.

## 1. Kod i regresja

Po push zmian:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
.venv/bin/python -B - <<'PY'
import os, shutil, sys, tempfile, unittest
root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos140-5-") as tmp:
    try:
        os.makedirs(os.path.join(tmp, "static", "js"))
        for name in ("session_generation.js", "terminal.js"):
            shutil.copyfile(os.path.join(root, "static", "js", name),
                            os.path.join(tmp, "static", "js", name))
        shutil.copyfile(os.path.join(root, "run.py"), os.path.join(tmp, "run.py"))
        os.chdir(tmp)
        os.environ["CHAOS_SESSION_FILE_DIR"] = os.path.join(tmp, "sessions")
        names = ["test_ghostnetwork_show_manifest", "test_ghostnetwork_signal_show",
                 "test_ghostnetwork_signal_show_http", "test_ghostnetwork_client_restart",
                 "test_ghostnetwork_transmission", "test_ghostnetwork_endgame_audits",
                 "test_ghostnetwork_signal_ranking", "test_ghostnetwork_signal_ranking_http",
                 "test_ghostsignal_historical_preview"]
        result = unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromNames(names))
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
```

Oczekiwane: 69 testów, OK. Następnie:

```bash
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/js/test_ghostnetwork_delta_client.js &&
node tests/ghost_signal_show_audio.test.js &&
node tests/js/test_game_sfx.js &&
node --check static/js/ghost_radio.js &&
node --check static/js/ghost_signal_show.js
```

Nie ma nowej migracji. Sprawdzenie istniejącego schematu:

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Oczekiwane `schema_change:false`. Po PASS:

```bash
pm2 reload chaos && pm2 reload chaos-territory-worker && pm2 status
```

## 2. Podgląd rzeczywistego finału 001

```bash
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-140-5-history.html
```

Przy istniejącym pliku wybierz nową nazwę. Zachowaj wypisany JSON:
`mode:historical`, `read_only:true`, obie checksum valid, counts, rozmiar i SHA
manifestu. Błąd danych przerywa generowanie, bez przełączania na DEMO.

Otwórz https://chaos.dmd-transport.pl/static/previews/ghostsignal-140-5-history.html.
Nagłówek musi mówić **REPLAY / DANE ARCHIWALNE**. Bez `--db` i `--cycle-id`
generator nadal tworzy jawnie oznaczone DEMO.

Odczyt SQLite używa mode=ro, query_only i jednej transakcji. Generator nie
inicjuje schematu, nie zapisuje projekcji, nie odczytuje ciężkich profili
ani świata live. Snapshot locka i ranking mają limit po 32 MiB.
HTML zawiera ograniczoną publiczną projekcję, w tym publiczne aliasy graczy.
Nie zawiera pełnego payloadu ani identyfikatorów prywatnych profili.

Historyczny finał 139 może nie mieć projekcji scen 140. Wtedy
`projection_reconstructed:true`: używamy zapisanych locka/rankingu i tego
samego adaptera wyników co runtime. Brak historycznej daty 2108 pozostaje
brakiem. Nie odtwarzamy nieutrwalonego pełnego świata ani fikcyjnych danych.
Publikacje i jawnie powiązane konflikty korzystają z dostępnych rekordów
z ograniczeniem czasu do utworzenia rankingu.

Porównaj części/topologię, sygnał i wersje, uczestników, RSP, nagrody,
terytoria i ranking z Signal Registry oraz raportem finału 139.
Nie wymagamy pełnych list tam, gdzie scena jawnie pokazuje ograniczony zakres.
Zegar podglądu jest przesunięty do chwili otwarcia strony. To rekonstrukcja
prezentacji danych; nie odtwarza pierwotnych opóźnień backendu, nie wysyła
sygnału, SFX, ACK ani restartu.

## 3. Desktop i telefon — 15 minut oraz recovery

Na desktopie i Redmi/telefonie o ograniczonej pamięci wykonaj osobny pełny
przebieg bez przewijania. Zapisz model, system, przeglądarkę, viewport i tryb
oszczędzania energii. Po 15 minutach kliknij **Raport wydajności** i zachowaj
JSON osobno dla każdego urządzenia. Pomiar zatrzymuje się po 920 s.

Raport obejmuje odstępy klatek w widocznej karcie, long tasks (jeśli API jest
dostępne), błędy JS, liczbę DOM, przejścia scen i próbki pamięci co 10 s.
Brak API pamięci daje null, nie zero. Nie wysyłamy telemetrii na serwer.
Mean frame time nie jest samodzielnym kryterium płynności. Sprawdź również
maksymalne przerwy i ich sceny, narastanie DOM/pamięci oraz zacięcia audio.
CPU/GPU i liczbę warstw sprawdź osobno w profilerze przeglądarki, szczególnie
podczas filmu i przejścia do settlementu; JSON ich nie mierzy.

W osobnym przebiegu sprawdź:

- seek do filmu, powrót z tła podczas filmu i po jego końcu;
- zmianę orientacji, reduced motion, mute i odmowę autoplay;
- brak MP3/video (DevTools), utratę i odzyskanie sieci;
- brak narastania elementów i odtwarzaczy po wielokrotnym seek;
- brak podwójnego audio, kontrolek filmu i ucieczki w fullscreen;
- granice miksu według [140.4](deploy_140_4.md), bez zmiany zaakceptowanego tempa.

Nie łącz raportu seek/stress z przebiegiem ciągłym. Zgłoś powtarzalne zacięcia,
błędy JS, niedziałający zegar lub zasoby pozostające po scenie. Wariant
offline podglądu sprawdza media; recovery API gry wymaga rzeczywistego show.

## 4. Bramka produkcyjnego E2E

Po odbiorze danych i urządzeń przygotuj świeży stan wejściowy: HEAD, PM2,
ID aktywnego cyklu, blokery, backup, worker verify i strict audyty
runtime/lifecycle. Nie korzystaj z dawnego checkpointu 139 jako dowodu
aktualnej gotowości. Restore bazy i zwolnienie konfliktów nie są częścią
komend podglądu; wymagają osobnej procedury dla wybranego aktualnego cyklu.

Przed operacyjnym triggerem uruchom istniejący monitor w osobnym terminalu,
wstawiając zweryfikowany ID cyklu:

```bash
cycle_id='WPISZ_ZWERYFIKOWANY_CYKL'
report_dir="data/audits/140-5-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$report_dir"
.venv/bin/python -B scripts/monitor_138_2_signal_e2e.py \
  --db data/game.sqlite3 --cycle-id "$cycle_id" --conflict-id '' \
  --output "$report_dir/monitor.jsonl" --summary "$report_dir/monitor.summary.json" \
  --pid-file "$report_dir/monitor.pid" --interval 2 --max-seconds 1800
```

Trzy sesje: desktop, mobile i sesja z powrotem z tła/reloadem. Potwierdź
wspólny czas/scenę i datę 2108, gate sygnału, SFX bez powtórki po reloadzie,
miks, ranking, trwały restart, nowy pulpit i Signal Registry. Sam koniec
900 s nie może zastępować backendowej epoki restartu. Monitor ma zakończyć
się bez błędów; przerwij Ctrl+C po zebraniu finału, jeśli nadal pracuje.

Raport końcowy dla tego samego cyklu:

```bash
.venv/bin/python -B scripts/audit_ghostnetwork_endgame.py \
  --db data/game.sqlite3 --cycle-id "$cycle_id" --strict --compact \
  --require-transmission-timeline
.venv/bin/python -B scripts/ollama_narrative_worker.py verify
.venv/bin/python -B scripts/audit_narrative_runtime.py --db data/game.sqlite3 --strict
.venv/bin/python -B scripts/audit_narrative_publication_lifecycle.py --db data/game.sqlite3 --strict
```

Do zamknięcia 140.5 potrzebne są: wyniki regresji na serwerze, zgodność
historycznych danych, raporty desktop/mobile, ręczny recovery/audio PASS,
monitor finału, poprawna chronologia oraz liczba restart receipts/ACK zgodna
z sesjami testowymi. Historyczne ostrzeżenia opisujemy oddzielnie od błędów.
PASS 139 i odsłuch 140.4 pozostają dowodami wcześniejszych etapów.
