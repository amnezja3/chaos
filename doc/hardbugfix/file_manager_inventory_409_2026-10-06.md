# FM: 409 przy brakującym ekwipunku konta — 6 X 2026

## Rozpoznanie

Użytkownik potwierdził, że `missing_generation` pochodziło z osobnego otwarcia
adresu API. Taka nawigacja nie wysyła nagłówka dodawanego przez klienta gry.
Nie wyłączamy walidacji generacji i nie akceptujemy starej sesji.

W izolowanej bazie odtworzono drugi błąd: prawidłowo uwierzytelnione żądanie
`GET /api/ghostlab/file-manager` zwraca `409 inventory_unavailable`, jeśli
brakuje wiersza `player_storage`. Rejestracja przez `profile_manager.registration`
tworzyła konto/projekcję/portfel, lecz nie inicjalizowała kanonicznego ekwipunku.
Wyjaśnia to różnicę między nowymi a wcześniej zmigrowanymi kontami. Nie
sprawdzano produkcyjnej bazy konta zgłoszonego przez użytkownika.

## Zmiana

- Rejestracja przygotowuje ekwipunek z istniejącego kandydata profilu przed
  blokadą zapisu, a magazyn, aplikacje i pliki zapisuje w tej samej transakcji
  co konto. Awaria wycofuje całe utworzenie konta.
- Inicjalizacja dotyczy wyłącznie nazwanego call site rejestracji. Nie zmienia
  semantyki importu starszych profili, normalnych zapisów ani odczytów.
- FM pozostaje lekkim odczytem kanonicznych tabel. Nie ma hydracji profilu,
  domyślnego pustego ekwipunku ani automatycznej naprawy podczas GET.
- FM pokazuje rozróżnione błędy ekwipunku/sesji/sieci i przycisk ponowienia.
  Wersja zasobu terminala została zmieniona w obu szablonach pulpitu.

## Starsze konta — po wdrożeniu

Samo wdrożenie nie zmienia danych już istniejących kont. Narzędzie offline
`tools/repair_file_manager_inventory.py` domyślnie audytuje dokładnie jedno
konto, bez zapisu. Uruchamiać na właściwej bazie aplikacji:

```sh
python tools/repair_file_manager_inventory.py --db /path/to/game.sqlite3 --username kot2
python tools/repair_file_manager_inventory.py --db /path/to/game.sqlite3 --username kot2 --apply
```

`ready` oznacza możliwość odtworzenia z profilu o poprawnym checksum/integrity.
`applied` oznacza atomowe utworzenie brakujących tabel ekwipunku dla tego konta.
`already_initialized` nie zapisuje niczego. Profil źródłowy pozostaje nietknięty,
retry nie duplikuje danych. Przed zapisem następuje ponowna kontrola wersji konta
i braku kanonicznych danych. Nie używać szerokiej migracji wszystkich store'ów
ani ponownego seedowania istniejącego ekwipunku do naprawienia tylko FM.

`partial_inventory_requires_review` oznacza, że istnieją już kanoniczne aplikacje,
pliki lub tombstone'y przy braku magazynu. Narzędzie odmawia wtedy odtworzenia
ze starego profilu, żeby nie przywrócić usuniętych plików/narzędzi. Taki przypadek
wymaga osobnego audytu danych. Brak poprawnej integralności też blokuje zapis.

## Weryfikacja

- Testy FM: nowa rejestracja, odtworzenie 409, dry-run/naprawa/retry, brak zmian
  profilu, odrzucenie częściowych danych i błędnego checksum, rollback oraz
  zachowanie odrzucenia brakującej/starej generacji sesji.
- Regresja ochrony profilu, rejestracji/portfela i GhostLab.
- Playwright na `tools/file_manager_browser_fixture.py`: rzeczywisty renderer FM,
  wrapper sesji i endpointy Flask, konto/baza tymczasowe. Nowe konto: 21 katalogów;
  symulowany brak inventory: czytelny błąd; naprawa i ponowienie: 21 katalogów,
  ten sam dysk 17/2048 MB. Brak błędów JS; jedyny błąd sieciowy to celowo
  wywołany 409 przed naprawą. To test komponentu, nie sesja produkcyjna.

Sprint 153 pozostaje lokalny i nie jest zależnością tej poprawki.
