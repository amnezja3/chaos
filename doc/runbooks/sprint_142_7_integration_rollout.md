# 142.7 — integracja i rollout wszystkich kont

21 IX 2026. Autor zlecił domknięcie sprintu po kontrolowanym odbiorze 142.6.
Status: **WDROŻONY / WYKONANIE POZA MAIN POTWIERDZONE** (21 IX 2026).
Autor wdrożył 5a0e404 i zrestartował wszystkie cztery procesy z update-env.
Odbiór mobile, live/reconnect na robot i obserwacja obciążenia VPS nie mają
jeszcze osobnego potwierdzenia; nie dopisujemy tych wyników automatycznie.

## Zakres rolloutu

W czterech ecosystemach `CHAOS_RESPONSE_EXECUTION_ACTORS` zmieniono z `main`
na `*`. `CHAOS_RESPONSE_EXECUTION_MODE=enforce`, kwalifikacja pozostaje `observe`.
To osobne bramki: OBS nadal opisuje kwalifikację; nie oznacza wyłączonych kar.
Konfiguracja dotyczy web, territory-worker, ollama-worker i narrative-publisher.
Zmiana lokalnych plików nie zmienia środowiska działających procesów VPS.

Nowe spotkanie każdego konta podlega szansom 80% inicjator / 30% postronny.
Stare avoided i not_enabled nie są ponawiane ani przekształcane w zaległe kary.
Nie czyścimy kartoteki ani historii. Stopnie 6–9 pozostają unsupported do 143;
nie zastępujemy aresztu mandatem i nie zwiększamy licznika za niewykonaną karę.

## Dowody odbioru autora

Na main wykonano stopnie 1–5: 30 HC, 62 HC, Nmap, Echo Needle + Blindfold Relay,
następnie 93 HC + Nmap + Glass Eye + Needle Implant. Nmap przed ponowną
konfiskatą został ponownie kupiony przez autora. Potwierdzone komunikaty,
trwałość wyników i konfiskaty po reconnectcie, dysk/pulpit/FM na żywo.
Avoided (85 przy progu 80) nie podniósł licznika; unsupported także nie.
OBS na już rozliczonym incident_b6bff287b8fe nie tworzył drugiej kary.

Robot: incident_d28d87911fe7, 21 IX 17:02:01 UTC, chance=80, roll=40,
executed, stage=5, mandat 150 HC i trzy narzędzia (Traceroute, ATM Logs,
Echo Needle), executed_count=1. Autor potwierdził eskalację L2 do L4 przed
wykonaniem kary; stopień 5 odpowiada L4 przy pustej kartotece.

## Wdrożenie po pobraniu kodu

```bash
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
pm2 startOrRestart ecosystem.ollama-worker.config.js --update-env
pm2 startOrRestart ecosystem.narrative-publisher.config.js --update-env
pm2 save
```

Weryfikacja wyłącznie czterech bramek konfiguracji (bez drukowania sekretów env):

```bash
pm2 jlist | .venv/bin/python -c 'import json,sys; names={"chaos","chaos-territory-worker","chaos-ollama-worker","chaos-narrative-publisher"}; keys=["CHAOS_RESPONSE_QUALIFICATION_MODE","CHAOS_RESPONSE_ENCOUNTERS_ENABLED","CHAOS_RESPONSE_EXECUTION_MODE","CHAOS_RESPONSE_EXECUTION_ACTORS"]; print(json.dumps([{ "name":p["name"], **{k:p["pm2_env"].get(k) for k in keys}} for p in json.load(sys.stdin) if p["name"] in names],indent=2))'
```

Oczekiwane observe / true / enforce / * dla wszystkich czterech procesów.
Nie wywoływać Ghost Signala ani resetu świata w celu aktywacji konfiguracji.

## Końcowy odbiór serwera

1. Konto inne niż main, online, nowy incydent L2 (nie wcześniejszy not_enabled).
   Przy selected oczekiwane executed, mandat i komunikat oraz aktualizacja HC.
   Avoided jest prawidłowe; potrzebny inny incydent, nie reset rzutu.
2. Sprawdzić reconnect i ponowne spotkanie tego samego incydentu: brak drugiej
   kary. Wariant mobile również odnotować jako rzeczywisty odbiór, nie domysł.
3. Sprawdzić log workera pod ruchem: brak powtarzającego się execution_retry_required,
   blocked i database contention. Pomiary VPS są osobnym dowodem od lokalnego baseline.
4. Kontrola offline i powrotu: brak skutków offline i brak odtwarzania historycznej
   pozycji; karę może spowodować dopiero prawidłowe aktualne spotkanie online.

Kontrola historii: zapytanie z runbooka 142.6 bez filtra main; porównać
execution_status, reason, plan.stage i effects z komunikatem i zasobami konta.
Przy pending zapisać powód przed jakąkolwiek ingerencją; nie usuwać receipts.

Kill switch: w czterech ecosystemach zmienić EXECUTION_MODE na `observe`
i powtórzyć startOrRestart z update-env. Zatrzymuje nowe skutki; nie cofa
wykonanych kar ani historii. Areszt/więzienia/blokady pozostają w sprincie 143.

## Pokrycie lokalne i granice dowodów

Zweryfikowano 113 różnych testów Python: 17 executora, 87 regresji pozostałych
etapów oraz końcowy zestaw 20 (11 powtórzeń kwalifikacji). Nowy test integracyjny
przed końcowym PASS wymagał poprawienia oczekiwania kary po spadku do L1
i oddzielenia mandatów od zdarzeń początkowego zasilenia portfela.
PASS także sześciu zestawów JS: inventory delta, camera delta/transport/dedupe,
incident version guard i 720 próbek kierunku NPC; składnia terminal.js,
odczyt/spójność czterech ecosystemów i git diff --check.

- `test_response_rollout_integration`: zapis canonical scanu, autoryzowany HTTP
  shutdown, spadek heat 62 → 58, dalsza eskalacja niezależna od kamer do L2,
  publiczne źródło/BlackNet i trwała publikacja oczekująca, dispatch patrolu,
  brak spotkania offline, wykonanie po powrocie online bez requestu z mapy,
  jeden mandat/ledger/kartoteka mimo kolejnych ticków. Ten test nie uruchamia
  rzeczywistego Overpass ani modelu Ollama.
- `test_camera_shutdown_contract`, `test_camera_exposure`: właściwa aplikacja,
  uprawnienia, zasięg, TTL/rescan/retry, kontrola bez shutdown i z shutdown,
  brak stackowania i przecieku osłony między graczami, canonical delty.
- `test_incident_lifecycle_publications`, `test_incident_narrative_retirement`:
  publiczne źródła i publikowanie BlackNet/Googleplex, expiry, retry publishera,
  niezależne cooling i długie operacje bez zależności od sesji inicjatora.
  Model językowy w tych testach zastępuje kontrolowany klient testowy;
  rzeczywisty przepływ był odebrany przez autora w 142.3.
- `test_response_qualification`: macierz 90 wariantów trzech visual_family,
  inicjator/postronny, online aktywny/nieaktywny/offline/wygasła sesja/timeout
  heartbeat, wewnątrz/na granicy/poza zasięgiem. Ruch w tej macierzy jest
  ustalony; rzeczywiste kapsuły i trajektorie sprawdzają osobne testy NPC.
- `test_response_encounters`, `test_canonical_consequences`: granice 30/80,
  współbieżność, crash/retry, zmiana epoki i obecności, ochrona zasobów,
  brak zaległych kar po rozszerzeniu allowlisty, nowy postronny z progiem 30.
- `test_detection_feedback_shadow`: HTTP sesja i prywatność wyniku;
  `test_consequence_table`: wspólna kartoteka i tabela etapów.

Baseline executora 21 IX, Windows, 10 próbek: mały profil p95 264,3 ms,
profil 35 MB p95 169,1 ms; writer-lock p95 odpowiednio 84,7 / 41,6 ms,
maksimum 43 instrukcje SQL; profile_full_read/write i profile_bytes = 0.
Wyniki zależą od lokalnego obciążenia; nie są pomiarem VPS ani SLA.
Nie dopisujemy produkcyjnego/mobile PASS bez odbioru autora.
