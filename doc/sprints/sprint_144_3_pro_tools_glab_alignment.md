# Sprint 144.3 — pro-toolsy: przypisanie GLab i lista potomstwa w adminie

Status: **PASS — ZAMKNIĘTY**, 25 IX 2026. Odbiór serwerowy potwierdzony przez użytkownika.
Runtime potomstwa pozostaje zakresem 145–146; PASS obejmuje kontrakty,
publikację, instalację, admina, listę PvP i zabezpieczenia wbudowanego Proxy.
Wdrożenie, migracja i odbiór: [runbook 144.3](../runbooks/sprint_144_3_glab_alignment.md).
Po [144.1](sprint_144_1_ghostlab_template_registry.md) i
[144.2](sprint_144_2_ghostlab_template_authoring.md), przed
[145](sprint_145_ghostlab_system_log_reader.md).
Osobny etap rozszerzenia, nie historyczna sekcja Publisher w bazowym 144.
Podstawa: [audyt 11 pro-toolsów](../audits/pro_tools_glab_audit_2026_09_25.md).

## Cel i podział pracy

144.1 dostarcza rejestr i kontrakt danych admina, 144.2 kreator, a 144.3
stosuje model do istniejących produktów i domyka widok admina oraz odbiór.
Logiki i przypisania dodajemy w kodzie. Admin nie tworzy wykonawców,
nie edytuje kontraktów i nie prowadzi dodatkowego obiegu certyfikacji.

## 1. Jawna klasyfikacja istniejących narzędzi

- GLab: systemLogReader, financialSniffer, friendKicker, securityPanelProxy,
  arsenalCleaner oraz intruderKicker (decyzja użytkownika z 25 IX).
  Pięć istniejących template_id zachować; dla Intruder Kicker przygotować
  kontrakt intruder_kicker oparty na istniejącym wykonawcy. Zachować wymóg
  intruza we własnym terytorium, aktywnego dostępu PvP i jedno użycie na dostęp;
  klony/nowe buildy nie mogą odnawiać limitu. Branding nie zmienia uprawnień.
- Nie-GLab na ten etap: victimPicker, territoryControl,
  operationControl, ghostnetworkSuite, agi2108Console.
- Każdy nowy systemowy pro-tool wymaga jawnej decyzji w kodzie. Test CI
  wykrywa brak przypisania i GLab bez poprawnego kontraktu. Test wylicza cały
  rejestr, nie tylko dzisiejszą stałą listę 11 ID.
- Samodzielny szablon bez source_tool_id jest poprawny. Produkt potomny
  nie staje się automatycznie nowym szablonem ani wbudowanym pro-toolsem.
- Przypisanie GLab nie włącza runtime przed 145–146 i nie zmienia cen,
  balansu, odbiorcy HC ani zasad dostępu wbudowanych narzędzi.

## 2. Zgodność danych i aktualizacji

- Spójny zapis klasyfikacji w rejestrze i projekcji katalogu; legacy writer
  nie może skasować powiązania. Zachować app_id, zakupy, instalacje i liczniki.
- Dry-run porównania katalogu serwera z rejestrem. Nie przypisywać autora lub
  rodzica po nazwie. Niejednoznaczne legacy raportować do wyjaśnienia.
- Powiązanie produktu z template_id, wersją kontraktu, projektem i autorem
  trwałe po rename, aktualizacji, withdraw i republish; build nie jest potomkiem.
- Nie uruchamiać ponownie migracji 37 obsłużonych kont. Jeśli potrzebna korekta
  metadanych, osobna idempotentna migracja z dry-run, bez dotykania profili.

## 3. Admin: szablony i produkty graczy

- Dokończyć widok z 144.1: rodzic, opcjonalny pro-tool źródłowy, stan dostępności,
  lista potomstwa. Pokazać nazwę produktu, autora, pobrania, datę stworzenia,
  aktualną cenę i status publikacji; filtrowanie oraz stronicowanie.
- Brak daty legacy oznaczyć jako brak danych. Nie używać daty migracji.
  Udokumentować, czy istniejący licznik pobrań liczy instalacje czy unikalnych
  użytkowników; nie nadawać mu nowej semantyki bez zmiany źródła.
- Dostęp admin-only; małe projekcje i indexed reads. Szkice nie są ofertami;
  wycofane produkty pozostają widoczne w historii potomstwa.

## 4. Panel PvP — lista rzeczywiście zainstalowanych narzędzi

Wymaganie użytkownika: usunąć wygaszone placeholdery nieposiadanych rodziców.
Obecne serialize_player_hack_access buduje stan z PLAYER_HACK_TOOL_IDS,
a frontend wyświetla także installed=false. Zastąpić to wspólnym resolverem
zainstalowanych narzędzi zgodnych z kontraktem Player Hack Access.

- Źródłem listy jest canonical inventory zalogowanego gracza oraz rejestr
  kontraktów, nie pełna lista rodziców i nie typ pro-system-tool sam w sobie.
- Pokazywać wbudowane narzędzia i potomstwo pod ich rzeczywistą nazwą i ikoną,
  z app_id i wersją zainstalowanego artefaktu. Posiadanie rodzica nie jest wymagane.
- Gracz z samym potomkiem widzi potomka; bez narzędzi widzi czytelny pusty stan.
  Przy posiadaniu rodzica i potomka oba pozostają odrębnymi produktami.
- Zainstalowane, ale chwilowo niedostępne narzędzie może mieć czytelny powód
  blokady (wykorzystany limit, brak kwalifikacji celu, runtime pending).
  To nie placeholder nieposiadanego produktu. Nie pokazywać narzędzi innych
  zastosowań, np. biletu lub rozszerzenia dysku, w panelu PvP.
- Refresh po instalacji, konfiskacie/uninstall, zmianie celu i wygaśnięciu dostępu.
  Serwer ponownie sprawdza własność, instalację, artefakt i dostęp przy użyciu;
  stary przycisk nie daje prawa do wykonania.
- Tożsamość produktu oddzielona od rodziny wykonawcy. Limity wspólne dla rodzica
  i potomstwa danej rodziny; klon nie daje dodatkowego użycia. Nie zamieniać
  app_id potomka na ID rodzica w requestach w celu obejścia walidacji instalacji.
- Lista i prezentacja w 144.3; uruchomienie SystemLogReadera w 145, pozostałych
  rodzin w 146. Runtime pending nie udaje działającego narzędzia.

## 5. Regresje i PASS

### Dodatkowe bramki po przeglądzie zależności (25 IX)

- **Krytyczne: security writer.** Obecne api_player_hack_security_update i preset
  używają load_profile_write_record oraz patch_profile_guarded. To potwierdzone
  naruszenie zero-heavy. W 144.3 wydzielić canonical zapis security i uzgodnić
  wszystkich jego writerów/odczyty, żeby starszy zapis profilu nie odtwarzał
  poprzednich zabezpieczeń. Nie zastępować go samą edycją desktop projection
  ani json_set poddrzewa profilu. Zachować transakcję, kontrolę wersji,
  SECURITY_CONFLICTS oraz ponowne sprawdzenie dostępu, instalacji i aresztu.
  Naprawa z regresją jest warunkiem PASS 144.3, nie zadaniem odłożonym do 146.
- **Dalsze akcje po otwarciu narzędzia.** Security update/preset wymagają dziś
  ID securityPanelProxy. Uogólnić kontrakt dalszych requestów tak, by potomstwo
  nie musiało posiadać rodzica; tożsamość produktu/artefaktu/dostępu związana
  z serwerowym kontekstem wykonania, a nie zaufaniem do danych klienta.
- **Wynik i branding.** Okna open*App mają nazwy rodziców (np. Intruder Kicker).
  Wynik potomka musi zachować nazwę, ikonę i wersję produktu; renderowanie po
  zatwierdzonym result_type/kontrakcie, bez uruchamiania dowolnej funkcji z JSON.
- **Migracja limitów.** Istniejące receipts keyed by tool_id muszą liczyć się
  do nowego wspólnego limitu rodziny. Wdrożenie nie daje drugiego użycia w już
  otwartym dostępie PvP. Test obejmuje receipt sprzed zmiany, klon i retry.
- **Pochodzenie produktu.** Kategorie/type/ghostlab_generated nie są dowodem
  zaufania. Tylko canonical publikacja, właściciel, artefakt i kontrakt mogą
  uruchomić executor; plik .glab i podrobiony wpis katalogu nie dają uprawnień.
- **Wyłączenie GLab.** Samo odebranie dostępności tworzenia nie unieważnia
  zainstalowanych produktów. Osobno wycofanie sprzedaży i blokada wykonania
  konkretnej wersji; zachować dane i czytelny powód dla użytkownika.

1. Wszystkie 11 narzędzi sklasyfikowane; nie-GLab nie pojawiają się w Templates.
2. Sześć GLab wskazuje poprawny kontrakt, ale runtime pozostaje kontrolowany.
   Intruder Kicker ma szablon i test granic kontraktu; wykonanie potomstwa w 146.
3. Nowy pro-tool bez decyzji powoduje błąd testu rejestru; definicja samodzielna
   i jawny nie-GLab przechodzą. Gracz nie może podrobić przypisania w requestach.
4. Admin poprawnie pokazuje Syslog, produkty dwóch autorów oraz legacy admina;
   rename/republish nie dublują potomstwa i nie resetują pobrań/dat.
5. Zakup, instalacja i istniejące launchery zachowują zachowanie i ceny.
   Wszystkie zmieniane ścieżki przechodzą testy zero-heavy, także odmowa i retry.
6. Runbook dodania narzędzia w kodzie: logika → klasyfikacja → kontrakt gdy GLab
   → testy → wdrożenie → sprawdzenie rodzica i potomstwa w adminie.
7. Raport zgodności produkcji, plan cofnięcia aktywacji bez kasowania danych
   oraz ręczny odbiór admina przed rozpoczęciem 145.
8. Panel PvP: brak narzędzi, sam rodzic, sam potomek, rodzic i potomstwo,
   kilka potomków jednej rodziny, wycofany lecz nadal zainstalowany produkt,
   konfiskata oraz niedziałający runtime. Brak placeholderów nieposiadanych rodziców.
9. Security update/preset nie czytają ani nie zapisują ciężkiego profilu;
   zmiana przez drugi writer, cofnięcie dostępu i uninstall w trakcie requestu
   nie nadpisują obcych zmian i nie pozwalają na nieuprawniony commit.

Obowiązuje [zakaz ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Wykryte naruszenie naprawiamy natychmiast w implementowanym zakresie z regresją;
nie odkładamy go do 145 ani nie uznajemy samego audytu statycznego za PASS.
