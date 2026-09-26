# GhostLab i kreatory — zakaz ciężkiego profilu, Sprinty 144–152

Status: **wiążący warunek implementacji i PASS**, dopisany 24 IX 2026 po przeglądzie
planów. Nie jest potwierdzeniem zgodności obecnego kodu. Dotyczy wszystkich etapów
144–152, również wywoływanych pośrednio istniejących helperów, middleware i workerów.

## Zakaz w ścieżkach aplikacji

**Dyspozycja autora dla 144–152: wykrycie → natychmiastowa naprawa.** Jeśli podczas
realizacji lub testowania któregokolwiek etapu ujawni się ciężki odczyt, zapis,
synchronizacja albo fallback profilu w jego ścieżce, naprawić go w tym samym etapie,
także gdy pochodzi ze starego helpera lub współdzielonego modułu. Nie kończyć na
wpisie w audycie, TODO, długu technicznym ani przeniesieniu problemu do kolejnego
sprintu. Wydzielić niezbędną projekcję/store, usunąć ciężką zależność i dodać test
regresji dla wykrytego przypadku. Etap pozostaje niegotowy do PASS do czasu naprawy
i weryfikacji. Sama zmiana dokumentacji nie oznacza naprawy istniejącego runtime.

Tworzenie/listowanie/edycja projektu, walidacja, preview, quote, compile, export,
publikacja, katalog, zakup, instalacja, uruchomienie, wykonanie skutku, odczyt wyniku,
retry, obsługa błędu i odświeżenie UI nie mogą:

- ładować ani deserializować całego `users.profile_json` autora, wykonawcy, celu
  lub odbiorcy płatności;
- używać `sync_session_profile()`, `UserStore.get_profile()`/`list_profiles()`
  ani równoważnego wrappera/SQL zwracającego pełny profil;
- zapisywać całego profilu, poddrzewa `files`/`apps` ani wykonywać read-modify-write
  ciężkiego dokumentu przez `save_profile()`, `UserProfileManager.update_profile()`
  lub bezpośredni SQL;
- uzupełniać brakujących danych runtime z `session['profile']`, legacy snapshotu
  albo domyślnego startera i zapisywać ich jako stanu kanonicznego;
- ukrywać ciężkiego odczytu za cache, background jobem, fallbackiem, pełnym endpointem
  `/profile`, bootstrapem kreatora lub odświeżeniem pulpitu.

Samo ponowne użycie istniejącego executora/instalatora nie jest wyjątkiem.
Jeśli narusza kontrakt, jego zależność trzeba odciąć lub wydzielić przed PASS
dotyczącego go etapu. Audyt zależności obejmuje cały request, nie tylko nową funkcję.

## Źródła danych

| Potrzeba | Docelowy kontrakt |
| --- | --- |
| Autor, nick, tożsamość odbiorcy | Ograniczona projekcja identity, konkretne konta |
| Poziom, respekt, profesja potrzebne do policy | Ograniczona projekcja progresji/tożsamości; tylko jawnie wymagane pola |
| Saldo i przelew | Canonical wallet i księga, transakcja/receipt |
| Posiadanie aplikacji, narzędzi, zajętość dysku | Canonical inventory/storage; zapytania zakresowe |
| Projekty, blueprinty, buildy | Dedykowany zapis projektów/artefaktów z rewizją; nie `profile.files` |
| Cel, dostęp, zabezpieczenia, kontakty, sankcje | Właściwy store domenowy lub wydzielona mała projekcja i writer |
| Wynik, logi systemowe, operacje, pliki | Store domenowy, paginacja/limity, konkretne identyfikatory |

Jeśli wymaganej projekcji/store jeszcze nie ma, jej dodanie jest częścią danego
sprintu — nie wolno zastąpić jej pełnym profilem. Selektywny odczyt pól musi mieć
jawny kontrakt i ograniczony zakres; nie pobierać dokumentu, żeby wyciąć pola w Pythonie.
Brak danych ma dawać jawny stan niedostępności/recovery, bez odbudowy całego profilu.

Zapis i delty pochodzą ze store kanonicznego. Nie dopuszczać kierunku
`legacy profile/session snapshot → canonical store` w zwykłym runtime.
UI odświeża tylko zmienione zakresy; osobno paginować listy projektów/buildów/plików.

## Migracja legacy — osobna ścieżka operatorska

Istniejące projekty w profilu mogą wymagać odczytu podczas migracji. Jest to jedyny
przewidziany tu wyjątek: dedykowane narzędzie offline, poza requestami i workerami
gry, z dry-run, jawną listą kont, ograniczonymi partiami, raportem i receipt/checkpoint.
Przenosi wyłącznie wybrane dane do właściwego store, idempotentnie i z kontrolą
rewizji. Nie nadpisuje profilu kanonicznym snapshotem ani nie inicjuje startera.
Runtime nie uruchamia migracji leniwie przy pierwszym otwarciu aplikacji.
Rollback wyłącza nową funkcję lub przywraca zgodną wersję store; nie przywraca
ciężkiego profilu jako źródła prawdy i nie cofa poprawnych transferów.

## Wymagana bramka testowa

1. Zinwentaryzować calle i SQL całej ścieżki, także auth, helperów quality/price,
   instalacji, bezpieczeństwa celu, notyfikacji i odświeżania UI.
2. Testy behawioralne ustawiają pełne read/write/normalizację profilu jako błąd.
   Sukces, odmowa, retry, reconnect i błąd zależności muszą nadal działać zgodnie
   z kontraktem na fixture canonical stores, bez pełnego profilu w sesji.
3. Dodać kontrolę SQL/telemetrię wykrywającą bezpośredni pełny odczyt/zapis
   `users.profile_json`, którego monkeypatch helpera by nie zauważył.
4. Dla każdego przebiegu odbioru raportować **0 ciężkich odczytów, 0 ciężkich
   zapisów i 0 pełnych synchronizacji profilu**. Oddzielny raport migracji.
5. Test współbieżności i kont A/B/target/odbiorca: żadnej podmiany tożsamości,
   utraty inventory ani salda. Mały zakres zmiany nie zapisuje obcego scope.

Naruszenie tej bramki oznacza FAIL etapu nawet wtedy, gdy UI i efekt gameplayowy
działają. W planach „profil działania” oznacza przepis narzędzia, nie profil konta.
