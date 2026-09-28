# Dodawanie szablonu GhostLab — kontrakt po 146.3

1. Zdefiniować kodowy kontrakt w `ghostlab_registry.py`: stabilne ID, kategoria,
   cel/launcher, pola z typami i granicami, wersje polityki/schematu/runtime,
   domyślne wartości, flagi tworzenia/publikacji i flaga wykonawcy. Nigdy nie
   uruchamiać dowolnego kodu pochodzącego z blueprintu.
2. Kreator korzysta z ogólnego edytora pól i walidacji. Kompilacja utrwala
   blueprint oraz branding. Zmiana semantyki wykonawcy wymaga świadomej zmiany
   `runtime_revision`; nie uznawać starych buildów za zgodne bez sprawdzenia.
3. `ghostlab_products.resolve` odczytuje instalację i historię opublikowanego
   artefaktu. Nie ufać flagom/nazwie przysłanym przez klienta ani kopii katalogu.
   Wycofana oferta blokuje nowe zakupy, ale nie zabiera opłaconych uprawnień.
4. Wybrać model zakupu i uruchomienia:
   - `travel_ticket`: zakup natychmiast realizuje jedną podróż i tworzy receipt;
     ocena wyłącznie od użytkownika, który odbył podróż.
   - `file_cleanup`: aplikacja wielokrotnego użytku, podpisany podgląd plików,
     ponowna kwalifikacja przy zapisie, tombstone chroniący przed odtworzeniem.
   - `system_update`: trwała instalacja wersji na konto/aplikację/artefakt;
     ta sama wersja nie jest wykonywana ponownie.
   - `security_restore`: podpisany wybrany preset i wersja zabezpieczeń,
     zapis CAS, rzeczywiste logi zmian i brak działania przy zgodnym stanie.
   - `firmware_update`: osobne opłacone uprawnienie do próby, parametry przypięte
     do zakupu, zapisany wynik losowania, wspólny cooldown, crash i bonusy.
5. Wykonanie i receipt w jednej transakcji z canonical stores. Nie odczytywać
   `users.profile_json`, nie wywoływać `sync_session_profile` i nie zapisywać
   pełnego profilu. Retry i dwie karty nie mogą powielić skutku lub opłaty.
   Zdarzenia UI i wiadomości wynikają z zatwierdzanego skutku.
6. Dodać własny renderer launchera tam, gdzie semantyka tego wymaga; ogólne okno
   konserwacji nie jest wykonawcą dowolnej aplikacji `own_system`. Escape HTML
   nazw/opisów, logi jako tekst, potwierdzenie kosztu/ryzyka przed operacją.
7. Panel admina `/api/admin/panel/list?section=ghostlab` automatycznie pokazuje
   registry i publikacje potomków z filtrem `template_id`, autorem, wersją,
   ceną, pobraniami i statusem. Nowe pola wymagają odrębnej projekcji; nie
   dopisywać ciężkiego odczytu profili w adminie.
8. Testy: niepoprawne pola, podrobiona instalacja, flagi/areszt, ponawianie,
   rollback, współbieżność, aktualizacja, odinstalowanie, wycofanie, izolacja kont,
   rzeczywisty efekt i brak heavy reads. Dodać runbook i sekwencję testów w grze.

Firmware rozszerza wyłącznie bramkę `action == "scan"` w `/map-action` i projekcję
efektywnego zasięgu `/api/ghostnetwork/ability`. `get_player_action_range` oraz
kanoniczne `action_range` nie są zmieniane: służą też innym akcjom, podróży i PvP.
