# Sprint 157.8 — raport implementacji lokalnej

17 X 2026. Kod przygotowany lokalnie; nie zmieniano konfiguracji ani danych produkcyjnych. Polityka 16+ i ochrona komunikacji mają niezależne flagi, domyślnie OFF. Nie nadano pełnego PASS produkcyjnego.

## Zakres wykonany

| Etap | Implementacja |
| --- | --- |
| 157.8.1 | Blokady oparte o ID kont, jawne zaproszenia i akceptacja, DM tylko między zaakceptowanymi kontaktami, limity, filtrowanie wypowiedzi i odtworzeń komunikacji. Kontrola przy transakcyjnym zapisie wiadomości. Bez zmian w autoryzacji walki i konfliktów. |
| 157.8.2 | Zgłoszenia wiadomości, profili i BlackNetu; dowody po sprawdzeniu dostępu zgłaszającego; panel administratora, uzasadnienia, ukrywanie, przywracanie, czasowe sankcje komunikacyjne i odwołania. Wstrzymanie źródła publikacji według source_scope. |
| 157.8.3 | Jedna bramka 16-v1, nowy kontrakt regulaminu 157-16-v1, brak automatycznej konwersji 18-v1. Historia blokad wieku, oznaczenie dawnych blokad do przeglądu, CLI rozstrzygnięcia z uzasadnieniem. |
| 157.8.4 | Projekty dokumentów PL/EN, narzędzie migracji, runbook, testy backendu i Playwright, lista warunków aktywacji. Odbiór produkcyjny pozostaje osobnym krokiem. |

## Ponowne użycie architektury

`communication_safety.py` rozszerza istniejące kontakty zamiast kopiować komunikator. `communication_safety_web.py` używa CSRF, generacji sesji i aktora Identity Gateway. Cyberner korzysta z dotychczasowego zapisu/deduplikacji w `response_network.chat_delivery`; ochrona działa wewnątrz jego transakcji. Ograniczenia nie są wpięte w autoryzację PvP.

Panel działa w istniejącym oknie ustawień CHAOS. Cyberner udostępnia wejście do ochrony kontaktu i zgłoszenie wiadomości; BlackNet zgłoszenie publikacji. Pełny panel `/account/safety` obsługuje też zgłoszenie profilu. Stare przyciski kontaktu kierują do jawnej obsługi zaproszeń.

Repozytorium narracji filtruje ukryte publikacje i wstrzymane źródła w odczytach użytkownika. Workery nie pobierają nowych zadań z wstrzymanego źródła, a publikacja rozpoczęta przed wstrzymaniem jest zatrzymywana przed materializacją. Już trwającego wywołania dostawcy AI nie anulujemy. Zachowujemy zadania i odbiory do wznowienia.

## Dowody testowe

- 66 testów PASS: communication_safety, communication_safety_web, identity_adult_policy, identity_gateway_web, cyberner_channel_routing, ghost_i18n, blacknet_languages. Log lokalny `.playwright-mcp/safety-regression.log`.
- Dodatkowy zestaw publikacji: 31 testów, 29 PASS, 2 istniejące błędy. Nowy test wstrzymania źródła PASS.
- Dwa błędy odtworzono przy załadowaniu `ghostnetwork/repository.py` z `git show HEAD`, bez lokalnych zmian tego modułu: `test_late_older_state_cannot_replace_active_head` (KeyError record), `test_newer_thread_state_invalidates_previous_head` (StopIteration). Log `.playwright-mcp/publication-baseline.log`. Pozostają nierozstrzygnięte; nie przypisujemy całemu zestawowi PASS.
- Playwright Chromium, lokalna jednorazowa baza: PL 1440 px i EN 390 px; blokada, odblokowanie, zgłoszenie, DOM, brak poziomego overflow i błędów JS. Narzędzie `tools/test_communication_safety_ui.py`; MCP Playwright nie był dostępny, użyto lokalnego pakietu.
- Testy JS izolacji generacji sesji oraz launch/resume PASS. Kontrola składni zmienionych skryptów PASS.
- Test migracji obejmuje dry-run, apply, idempotencję i porównanie dotychczasowych danych. Test zapisu wiadomości potwierdza brak zapisu po blokadzie; test synchronizacji zachowanie payloadu PvP.

## Dane i granice ochrony

| Dane | Zapis i dostęp | Ustalenia przed aktywacją |
| --- | --- | --- |
| Blokady i zaproszenia | ID kont, daty, stan; własne relacje w panelu | Nie udostępniać listy osób, które zablokowały użytkownika |
| Limity | ID konta, rodzaj operacji, okno i licznik | Polityka czyszczenia nieaktywnych liczników |
| Zgłoszenia | Rodzaj i klucz obiektu, kategoria, opis, ograniczona kopia treści | Podstawa, retencja, dostęp administratorów, procedura realizacji praw |
| Decyzje | Uzasadnienie, działanie, czas, autor; historia odwołań | Obsada, czas reakcji, pilne zagrożenia i procedura odwoławcza |
| Oświadczenia wieku | ID konta, wersje, czas, boolean; bez daty urodzenia | Finalny regulamin i ocena proporcjonalności deklaracji |
| AI | Dotychczasowe wejścia narracji i publiczne projekcje; źródła można wstrzymać | Pełny wykaz dostawców i rzeczywistych przepływów wszystkich agentów |

Usunięcie konta usuwa relacje kontaktowe i odłącza identyfikatory zgłoszeń. Dowody mogą nadal zawierać nick lub treść osobową; nie nazywamy tego anonimizacją. Nie wdrożono arbitralnej retencji bez decyzji operatora.

Moderacja jest ręczna i przypisana do istniejącego administratora `admin`. Nie ma automatycznego rozpoznawania wszystkich rodzajów szkodliwych treści ani gwarancji bezpieczeństwa każdego agenta AI. Filtry narracji nie zastępują obsługi zgłoszeń.

Zgłoszenia wiadomości i publikacji rozwiązywane są w obrębie do 100 ostatnich dostępnych rekordów. Panel zgłoszeń pokazuje do 100 ostatnich spraw; paginacja i obsługa starszych obiektów pozostają ograniczeniem wersji początkowej. Ukrycie nie usuwa kopii wcześniej pobranych przez klienta. Liczniki nieprzeczytanych wiadomości mogą uwzględniać ukryte wypowiedzi; ich treść jest filtrowana.

## Przed produkcją

Nie aktywować 16+ przed zatwierdzeniem dokumentów i decyzji wskazanych w [runbooku](../runbooks/safety_157_8_rollout.md). Ochronę komunikacji można wdrażać oddzielnie po ustaleniu obsługi moderacji i danych zgłoszeń. Potrzebny odbiór prawdziwych dostawców, PWA i scenariuszy w świecie gry. Dwa błędy bazowego zestawu narracji wymagają osobnego rozstrzygnięcia przed pełnym PASS.
