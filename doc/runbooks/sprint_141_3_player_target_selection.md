# 141.3 — wybór celu PvP z mapy i projekcja zabezpieczeń

Status 15 IX: pakiet lokalny; wymaga jawnego backfill przed uruchomieniem
nowego wyboru celu na istniejącej bazie. Nie wykonano deployu ani migracji
bazy projektu/serwera. Nie zamyka całego 141.3.

## Kontrakt

`/api/map/player-targets/mark` korzysta z `build_visible_player_actors`, tak samo
jak snapshot mapy. Ograniczona projekcja wybiera aktualnie widoczne konta
według pozycji, relacji i geometrii. Historyczny intruder event ani ręcznie
wpisany username nie wystarczają. Self/friend/same clan i brak attackable
blokują wybór. Zasięg pochodzi z capability, obie pozycje z canonical stores.

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
