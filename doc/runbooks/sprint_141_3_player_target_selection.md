# 141.3 — wybór celu PvP z mapy i projekcja zabezpieczeń

Status 15 IX: operator wykonał backfill 31 kont bez pominięć, verify READY
przed i po uruchomieniu czterech procesów CHAOS. Autor odebrał wybór celu
w grze (Neo1/Krymek), blokady znajomego/klanu i zachowanie postępu.
Nie zamyka całego 141.3. Procedura poniżej pozostaje instrukcją referencyjną,
nie poleceniem powtórzenia migracji.

## Kontrakt

`/api/map/player-targets/mark` korzysta z `build_visible_player_actors`, tak samo
jak snapshot mapy. Ograniczona projekcja wybiera aktualnie widoczne konta
według pozycji, relacji i geometrii. Historyczny intruder event ani ręcznie
wpisany username nie wystarczają. Self/friend/same clan i brak attackable
blokują wybór. Zasięg pochodzi z capability, obie pozycje z canonical stores.

Decyzja autora z odbioru: utrata widoczności/zasięgu blokuje nowe i ponowne
oznaczenie, lecz nie przerywa rozpoczętego hacku. Cel po opuszczeniu terytorium
znika z mapy, pozostaje w Victim Pickerze z odległością i pozwala kontynuować
namierzanie/otaczanie/hack. Dalsza walidacja capture musi uznawać kanoniczny
stan rozpoczętego hacku, zamiast ponownie wymagać warunków nowego oznaczenia.
To nie uprawnienie do dowolnego niewidocznego konta podanego przez klienta.

Zapis przechodzi przez `upsert_player_aimed_target_runtime`, zachowuje ID
`player:<username>`, postęp security/actions i hook aktywnej zdolności GN.
Nie zapisuje ciężkiego profilu ani jego kopii w sesji. Odmowa canonical store
nie jest maskowana sukcesem. Odpowiedź niesie canonical target i wersję pozycji.

Security jest nadal kanonicznie polem profilu. Jego wąska projekcja
`desktop_boot_json.player_security` aktualizuje się atomowo przy guarded write.
Odczyt sprawdza revision/checksum/integrity. Limit: 128 pól bool/int, klucze
do 128 znaków, liczby w zakresie ±(2^63−1). `descriptions` jest pomijane jako
metadane prezentacji. Niepoprawny stan daje recovery, bez full-profile fallbacku.
Pusty poprawny słownik zachowuje dotychczasowy fallback szablonu zabezpieczeń.

## Migracja operatora

To rozszerzenie istniejącej migracji identity, nie nowy profil ani nowa baza.
Status ma teraz `player_security_missing`; historyczne READY z 141.2 nie
potwierdza obecności nowego pola. Backfill nie zmienia profilu, pozycji,
receiptów ani nagród. Zachowuje ponowne sprawdzenie CAS pod writer-lockiem.

Operator potwierdza bazę używaną przez proces; historycznie była to
`/home/johndoe/app/chaos/data/game.sqlite3`. Po udostępnieniu nowego kodu,
przed uruchomieniem zmienionych ścieżek:

1. Wykonać `status` i pełny `dry-run` po jednej pozycji. CLI dry-run zwraca
   jedną stronę: kolejne wymagają `--after-username` z `next_cursor`, aż `done`.
2. Przejrzeć pominięcia; nie wykonywać automatycznej naprawy profili.
3. Zrobić spójną kopię przez SQLite backup API i sprawdzić `quick_check` kopii.
4. Wykonać jawny apply, następnie verify. Uruchomić nowe procesy dopiero
   po READY. Stary writer może ponownie usunąć pole z projekcji, dlatego po
   przełączeniu wszystkich writerów wymagane jest ponowne verify.

Komendy referencyjne (nie są poleceniem automatycznego wykonania):

```bash
.venv/bin/python -m tools.migrate_identity_projection status --db data/game.sqlite3
.venv/bin/python -m tools.migrate_identity_projection dry-run --db data/game.sqlite3 --batch-size 1
.venv/bin/python -m tools.migrate_identity_projection apply --db data/game.sqlite3 --batch-size 1 --confirm-apply
.venv/bin/python -m tools.migrate_identity_projection verify --db data/game.sqlite3
```

Warunek: READY, missing/stale/map_avatar_missing/player_security_missing = 0.
Bez wykonania kroku 3 nie przechodzić od dry-run do apply. W razie braków
po przełączeniu writerów przejrzeć konta i jawnie uzupełnić projekcje ponownie.
Nie stosować restore ani profilu jako runtime fallbacku.

## Walidacja i dalszy zakres

### Pakiet lokalny po odbiorze gameplayu — 15 IX

Autor zaakceptował obecny gameplay. Picker używa identity/capability, canonical
inventory/position/target oraz wspólnej projekcji widocznych aktorów. Aktualny
cel pozostaje śledzony poza widocznością; odległość wynika z bieżącej pozycji,
a ponowne oznaczenie pozostaje zabronione. `/api/map/aim-target` dla gracza
przechodzi przez tę samą bramkę co mark; usunięto osobny fallback pełnego profilu.

Player-mode `/gonna-win` używa bounded context i canonical operations, nie
zastępuje sesji niepełnym profilem ani nie wysyła pustego `hacked` jako resetu.
Zachowano `operation_only`, osobny postęp i wymóg ukończenia zabezpieczeń/kropek.
Nowa tabela `player_hack_capture_receipts` przechowuje trwały wynik. Jedna
transakcja obejmuje recheck target key/version/progress, grant, terminal target
i zapis wyniku. Odczyt replay jest przed krótkotrwałym receipt aplikacji;
czas dostępu wyliczany ponownie, bez odnowienia po wygaśnięciu. Cooldown blokuje
nowe przyznanie po wygaśnięciu poprzedniego dostępu. Bieżąca relacja jest
sprawdzana przed wykonaniem oraz przed commit capture, bez warunku zasięgu
dla kontynuacji.

Nowa tabela powstaje przy standardowym init schema; nie ma backfill historycznych
grantów ani potrzeby ponawiania migracji security dla tego pakietu. Stare wyniki
nie otrzymują retroaktywnie trwałych receiptów. Pakiet nie został wdrożony.

Testy: 97 Python PASS w przebiegu regresji; po dodatkowej kontroli cooldown
11 capture/grant PASS (98 różnych testów łącznie). JS gonna-win lifecycle
i player actor position order PASS. Symulowane awarie przed terminal target
oraz po commit/przed receipt aplikacji, concurrency, A/B mismatch, ciężkie
profile ≥35 MiB, kontynuacja poza terytorium i replay po wygaśnięciu.

**Pozostałe domknięcie techniczne:** `/hack-action` nadal ładuje profil;
`set_player_aimed_target` zapisuje tam wspólnie launch_queue, risk_events
i system_messages. `UserStore.consume_launch_queue` czyta pełny profil nawet
dla pustego pollingu. `append_risk_event` w tej ścieżce buduje dane profilu.
Trzeba przenieść te dane do canonical stores z zachowaniem deduplikacji,
odbioru kolejki i historii ryzyka. Nie wprowadzono jeszcze zapowiedzianej
projekcji wskaźnika kolejki; plan wymaga uwzględnienia wszystkich writerów.
Nie jest to blokada odbioru gameplayu, lecz otwarta bramka hot path 141.3.

Testy izolowane: wybór na dwóch profilach ≥35 MiB bez pełnych odczytów,
canonical coordinates/version, zachowanie postępu przy retry, niewidoczny
teleportowany cel, zasięg, self/klan/znajomy, brak projekcji i jawny backfill,
limit security oraz aktualizacja projekcji przy guarded mutation.

Odbiór w grze po migracji: wybór intruza w zasięgu; odmowa po teleportacji
poza widoczność i poza zasięg; brak wyboru znajomego i własnego klanu; ponowny
wybór zachowuje postęp. Pozostałe ścieżki nie są objęte tym pakietem:
Victim Picker i alternatywne wejście target security nadal wymagają cutover,
capture wymaga ponownej walidacji przed grantem, a grant — trwałego powiązania
z receipt operacji także po wygaśnięciu. Sprawdzenie przy wyborze nie zastępuje
sprawdzenia przy przełamaniu; ruch/relacja mogą zmienić się między requestami.
