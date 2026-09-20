# 142.5 — trwałe spotkania i losowanie

Status: implementacja lokalna, oczekuje na deploy i odbiór autora.
Reguła zatwierdzona 20 IX 2026: jeden rzut na parę gracz–incydent.

## Zachowanie

`response_encounters` przechowuje rolę, szansę, rzut 1–100, wynik,
czas i snapshot kwalifikacji. Inicjator ma 80%, postronny 30%.
`selected` oznacza wylosowanie konsekwencji, `avoided` jej uniknięcie.
Oba wyniki są trwałe. `execution_status=not_enabled`: etap 142.5 nie pobiera
HC, nie konfiskuje narzędzi i nie pokazuje komunikatu o wykonanej karze.
Na mapie nadal OBS. Wykonanie/recovery kar należy do 142.6.

Endpoint mapy i worker korzystają z tego samego store'u. Kwalifikacja jest
ponawiana w transakcji `BEGIN IMMEDIATE`, na tej samej connection co receipt:
sesja, presence, pozycja, incydent i patrol. Dopiero wtedy odczyt istniejącego
wyniku lub jeden rzut i INSERT. Ograniczenie UNIQUE obejmuje aktora, incydent
i serwerowe `occurrence=1`. Payload nie może wybrać occurrence, roli ani rzutu.
Powtórki, zmiana patrolu/obserwatora, reconnect i restart nie losują ponownie.
Nowy incydent ma osobny wynik. Kolejne zatrzymania w 143 wymagają odrębnej,
zatwierdzonej polityki occurrence; retry nie jest recydywą.

Inicjator pochodzi z trwałych suspect_refs, także bez aktywnej operacji.
Offline nie powstaje receipt; po powrocie liczy się aktualne położenie i
obecność, bez odtwarzania starego zgłoszenia. Warunki kwalifikacji z 142.4
pozostają aktywne. Endpoint udostępnia szczegóły losowania tylko jego aktorowi.

## Koszt detekcji

Territory-worker sprawdza maksymalnie 4 patrole i po 16 kandydatów na patrol
w cyklu operation runtime (domyślnie 2 s po zakończeniu poprzedniego cyklu).
Patrole mają indeksowany czas ostatniego sprawdzenia oraz kursor użytkownika.
Nawet nieprawidłowy patrol oddaje kolejkę następnym. Zatłoczony obszar jest
stronicowany; pełny obieg nie musi zmieścić się w jednym cyklu.

Kandydaci pochodzą z indeksu lat/lng `player_positions` i heartbeat
`mail_presence`; zapisane pary gracz–incydent są pomijane przez indeks UNIQUE.
Dokładny dystans, własność sesji i source są sprawdzane przed losowaniem.
Brak ładowania profili i pętli wszyscy gracze × wszystkie patrole.
Mapa nie musi być otwarta; zalogowany desktop musi podtrzymywać presence.

## Deploy

We wszystkich czterech ecosystemach:
`CHAOS_RESPONSE_QUALIFICATION_MODE: "observe"`,
`CHAOS_RESPONSE_ENCOUNTERS_ENABLED: "true"`.
Bez flagi encounters domyślnie false (dotychczasowa obserwacja 142.4).
Wyłączenie kwalifikacji wyłącza również losowanie i skan workera.
Tabela receipt, indeks i dwa pola kursora patrolu powstają przy starcie.
Nie usuwać receipts podczas restartu ani rollbacku flagi.

Po pobraniu kodu na VPS:

```bash
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
pm2 startOrRestart ecosystem.ollama-worker.config.js --update-env
pm2 startOrRestart ecosystem.narrative-publisher.config.js --update-env
pm2 save
```

## Odbiór i diagnostyka

1. Inicjator i gracz postronny wchodzą w zasięg patrolu: po jednym zapisie
   na każdego, odpowiednio chance 80 i 30. HC i narzędzia bez zmian.
2. Powrót w zasięg, drugi patrol, obserwator, reconnect oraz restart workera:
   ten sam encounter_id, rzut i wynik, brak dodatkowego rekordu tej pary.
3. Gracz pozostaje online z zamkniętą mapą, gdy patrol przechodzi obok:
   receipt może utworzyć worker; nowe zapisy potwierdza jego log.
4. Offline brak nowego wyniku. Powrót online poza zasięgiem również go nie
   tworzy; dopiero bieżące spotkanie w zasięgu. Samo zamknięcie przeglądarki
   wymaga odczekania okna presence 90 s.

Nie trzeba uzyskać obu losowych wyników w małej próbie gameplay: progi
30/31 i 80/81 oraz trwałość avoided są sprawdzane deterministycznymi testami.

Ostatnie wyniki, odczyt bez importowania aplikacji i bez modyfikacji bazy:

```bash
.venv/bin/python - <<'PY'
import sqlite3
from contextlib import closing
with closing(sqlite3.connect('file:data/game.sqlite3?mode=ro', uri=True)) as db:
    rows = db.execute('''SELECT created_at,actor_id,incident_id,actor_role,
        chance,roll,outcome,execution_status,encounter_id
        FROM response_encounters ORDER BY created_at DESC LIMIT 30''')
    for row in rows:
        print(' | '.join(map(str, row)))
PY
```

Log workera po nowych zapisach zawiera `response_encounters` z licznikami
patrols/candidates/created/duplicates. Brak nowych zapisów nie generuje logu.

## Walidacja lokalna

58 testów PASS (izolowany runner): response_encounters,
response_qualification, detection_feedback_shadow,
territory_worker_ghostnetwork_fairness, camera_exposure,
response_npc_frontend_contract, response_network_safety.
Obejmują równoczesne zgłoszenia, restart store'u, zmianę patrolu,
progi 30/31 i 80/81, zapis avoided, rollback błędnego rzutu,
offline i powrót w innym miejscu, stronicowanie i pomijanie uszkodzonego
patrolu, prywatność receipt w endpointcie oraz brak wykonania kar.
Obciążenie produkcyjne i odbiór gameplay pozostają do sprawdzenia po deployu.
