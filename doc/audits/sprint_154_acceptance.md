# Sprint 154 — odbiór lokalny 154.7.0

8 X 2026. Pakiet: **2833 klucze PL/EN, 13 domen**. Implementacja pozostałych
workspace’ów, katalogów i ścieżek narzędzi przygotowana lokalnie. Produkcyjny
PASS dotyczy nadal wyłącznie 154.5.0; 154.7.0 nie został wypchnięty ani wdrożony.

## Pokrycie

| Zakres | Implementacja i dowód |
| --- | --- |
| Territory Control, Victim Picker, Operation Control | Sekcje, statusy, filtry, puste stany, anulowanie; `control_workspaces_locale.js`, `operation_control_locale.js`, regresje backendu terytoriów i operacji |
| Ghost Network Suite, Signal Registry, Sender | Grupy i widoczność danych, nawigacja, ranking/archiwum, etapy transmisji, blokada i recovery; `network_workspace_locale.js`, `pvp_families_locale.js`, testy Suite/Registry/audio. Sender pozostaje ścieżką transmisji, nie nową aplikacją |
| Googleplex | 38 produktów kodowych, 20 starszych aplikacji systemowych; nazwa, opis, specyfikacja, aliasy PL/EN, filtrowanie, potwierdzenie zakupu, instalator, aktualizacja; `googleplex_locale.js`, `test_catalog_locale.py`, zestawy JS zakupu/aktualizacji |
| Starsze instalacje | Metadane języka dołączane przy odczycie, bez reinstalacji i zapisu inwentarza. Zmienione pola autora pozostają dosłowne. `test_catalog_locale.py`, `legacy_tools_locale.js` — cztery interfejsy i niezmienne ID akcji |
| GhostLab | 13 szablonów, 59 pól, projekty, edytor, walidacja, kompilacja, publikacja, wersje, aktualizacja, dokumenty, Documentation/Research/Exchange; `ghostlab_locale.js`, backend registry/runtime/publication oraz mutacje |
| Cztery kreatory | Aktualny edytor oraz dostępny fallback: etapy, opcje, pomoc, błędy, publikacja; `creator_editor_locale.js`, `creator_fallback_locale.js`. Szkic i wybrany kontrakt zachowane przy zmianie języka |
| Sześć rodzin PvP | Log Reader, Security Panel Proxy, Financial Sniffer, Friend Kicker, Arsenal Cleaner, Intruder Kicker: dostęp, wykonanie, odmowa, cooldown, wynik; `pvp_families_locale.js` i backend kupujący/publikujący/używający produkty na osobnych kontach |
| Serwis i skanery | Konserwacja, cleanup, zabezpieczenia, firmware, Deep Scanner: podgląd, potwierdzenie, użycie, retry, aktywacja i zwolnienie; `service_workspace_locale.js`, testy backendu i JS usług |
| Bilety i ulepszenia | Oferty systemowe, miasta, ceny, wymagania, zakup/instalacja, podróż i ograniczenia; wspólny katalog, `test_ghostlab_travel.py`, `test_ghostlab_travel.js`, kanoniczne transakcje portfela |
| Ghost Exchange | Kategorie, kompletowanie, statystyki, historia, komunikaty API oferty/sprzedaży i ponowienia; `communications_locale.js`, testy kopert oraz transakcji. Obecny dashboard nie wystawia starszych ręcznych przycisków preview/sell |
| Cyberner, BlackNet, AGI | Kanały i formularze, zachowanie szkicu, wysyłanie, CTA/teleport, status zadania; `communications_locale.js`, `remaining_workspace_locale.js`. Treść wiadomości i publikacji nie jest tłumaczona w tej warstwie |
| Mapa i picker | Wspólne nazwy akcji, dopasowanie narzędzia, wyniki, blokady, cooldown, operacje, podatności, profil obiektu/gracza. Nowe NPC i kamery mają jawne klucze prezentacji; nazwa kanoniczna nie zmienia ID ani żądania. Testy `map_*_locale.js`, `test_scan_marker_categories.py`, `test_map_action_locale.js` |
| Radio | PL/EN/ANY, niezależny zapis filtra, bez restartowania utworu po zmianie UI; `radio_locale.js`, `test_radio_locale.py`. Audycje BlackNet 001–009: PL potwierdzone przez autora; 25 pozostałych nagrań: unknown, dostępne przez ANY |
| Dev Bug Reporter | Formularz, kategorie, walidacje, potwierdzenie i błędy; `bug_report_locale.js`, backend zgłoszeń. Zgłoszenie autora pozostaje bez zmian |

## Sposób weryfikacji

Playwright MCP uruchamiał rzeczywiste renderery desktopu przez
`python tools/sprint_153_browser_fixture.py`, z izolowanym kontem i atrapami
zewnętrznych integracji/API. Testy obejmowały PL/EN, przełączenie otwartego
interfejsu, mobile 390 px, UGC przypominające HTML/klucz słownika, szkice,
anulowanie oraz niezmienne payloady. Bez wyjątków JavaScript w zaliczonych
scenariuszach. Radio używa atrapy Audio do sprawdzenia źródła i czasu odtwarzania.

Backend był testowany osobno na izolowanych bazach: rzeczywiste zakupy,
publikacje, instalacje, użycie, retry, rollback, blokady i rozliczenia.
Końcowy wspólny przebieg: **287/287 testów Python PASS** (198,850 s).
Obejmuje katalog/i18n, GhostLab registry/runtime/mutacje/serwis/firmware/skanery/
podróże, portfel, radio, Territory/Operation Control, Suite, AGI, map actors,
starsze kreatory, kontrakt wyników operacji, kategorie skanu i obronę terenu.
Starsze testy odczytujące źródła z cwd otrzymały ścieżki względem repozytorium;
asercje etykiet używają teraz kluczy i katalogu zamiast tekstu zaszytego w JS.
Nie jest to test pełnego świata produkcyjnego ani odsłuch wszystkich audycji.

Powtarzalna regresja frontendu: `node tools/check_sprint154.cjs` — **30/30 PASS**.
Katalogi PL/EN mają zgodne klucze, parametry i wersje. `git diff --check` PASS.
Szczegółowe testy przeglądarkowe znajdują się w `tests/browser/`.

## Granica z 155

EN pozostaje wersją testową do końcowego odbioru 155. Tam pozostają wcześniej
zaplanowane: trwałe wiadomości/eventy i ich historia, narracja Ollamy/BN/News,
sceny oraz media Ghost Signal Show, konsekwencje i dokumenty systemowe.
Historycznych nazw bez jawnego pochodzenia nie tłumaczymy heurystycznie.
Techniczne kody transmisji/checksum/receipt nie zmieniają języka.

UGC, nazwy marek, komendy, ścieżki plików, ID, kwoty i efekty nie są tłumaczone.
FM `/about` i `/tip&trick` pozostają bez zmian; kolejne wersje treści należą do 155.
Sprinty 149–152 i GhostLab v2 pozostają zamrożone.
