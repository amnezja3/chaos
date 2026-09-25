# 144.1 — rejestr kontraktów GhostLaba

25 IX 2026. **PASS — odbiór serwerowy potwierdzony przez użytkownika.**
Potwierdzono Templates i istniejący Syslog, ponowną publikację bez duplikatu,
refresh WebDragona po poprawce, utworzenie/Compile Friend Kickera oraz odmowę
zapisu success_percent=86 i poprawny zapis po przywróceniu dozwolonej wartości.
Nie jest to odbiór działania runtime potomstwa.

## Co zmieniono

- `ghostlab_registry.py`: pięć obecnych definicji, schema pól, domyślne wartości,
  zakresy i pola zablokowane, wersje kontraktu/schema/policy, metadane katalogu,
  kontrakt aplikacji, przełączniki tworzenia/publikacji i jawny brak runtime.
- `PRO_TOOL_GLAB` wymaga decyzji dla każdego wbudowanego pro-toolsa. Intruder
  Kicker wskazuje planowany kontrakt; nie jest jeszcze udostępniony jako szablon.
- Trasa GET `/api/ghostlab/templates` wymaga sesji, nie otwiera profilu ani DB.
  Templates pobiera listę z backendu, edytor używa `field_schema` z odpowiedzi
  projektu. Walidacja backendu pozostaje autorytatywna.
- Compiler i Publisher używają tego samego rejestru. Nowy build wiąże wersję
  kontraktu i prezentację. Zmiana wersji wymaga nowego buildu; stare artefakty
  pozostają niezmienne. Artefakty bazowego 144 bez contract_version są zgodne
  z kontraktem 1, jeśli zgadza się schema/policy i runtime_contract.
- Flaga runtime sama nie daje wykonawcy: runtime w 144.1 jest zawsze niedostępny.
  Podłączenie wykonawców nastąpi w 145/146. Nie dodano nowej migracji danych.
- Planowane kontrakty przyszłych rodzin są oddzielone od aktywnego katalogu.
  Branding twórcy i admin/PvP pozostają dalszym zakresem 144.2/144.3.

## Dodawanie narzędzia / szablonu w kodzie

1. Dodać logikę narzędzia i jawne przypisanie PRO_TOOL_GLAB, także dla nie-GLab.
2. Dla GLab dodać definicję TEMPLATES (lub jawny niedostępny PLANNED_CONTRACTS).
   Definicja samodzielnego szablonu może mieć source_tool_id=None.
3. Określić fields, default, typ, editable, granice; app_contract, cel i launcher,
   wynik, wersje i dostępność. Zachować zasadę jednego konkretnego przeznaczenia.
4. Zmiana semantyki kontraktu wymaga nowej wersji i testów zgodności artefaktów;
   nie edytować zapisanych buildów. Rejestr nie jest loaderem kodu użytkownika.
5. Uruchomić testy registry/publication i test formularza. Test nowej definicji
   musi przejść bez dopisywania list do routes, compiler/publisher i UI.

Konfiguracja rejestru jest w kodzie, bez nowych env. Jeśli pojawią się zmienne
wdrożeniowe, umieszczać je w ecosystemach zgodnie z regułą projektu.

## Wdrożenie i test serwerowy

Po dostarczeniu kodu:

```bash
pm2 startOrRestart ecosystem.web.config.js --update-env
```

Ctrl+Shift+R. Nie powtarzać migracji kont z 144.

1. main: Templates pokazuje pięć dotychczasowych szablonów, poprawne ikony i runtime pending.
2. Otworzyć istniejący Syslog: log_limit i polityka redakcji zachowane;
   pole redakcji nieedytowalne. Zapis → Compile → Publish działa.
3. Utworzyć testowy projekt innego szablonu; sprawdzić formularz, wartości
   początkowe i odmowę poza zakresem. Wycofanie publikacji nadal działa.
4. admin: oba legacy projekty widoczne; bez utraty app_id, zakupów i historii.
5. DevTools: GET templates zwraca 200 dla zalogowanego, pola fields i wersje;
   brak requestów do profilu podczas pobierania listy szablonów.

Nie uznawać runtime potomstwa ani całego zero-heavy wykonania PvP za sprawdzone
tym etapem. Potwierdzona wada security writer jest bramką 144.3.
Wyłączenie creation/publication nie kasuje danych; runtime pozostaje pending.
Przy problemie zachować DB i artefakty, poprawić kod lub wyłączyć publikację
w definicji. Nie cofać danych graczy przez odtwarzanie całej bazy.

## Testy lokalne

Wynik 25 IX: **23 testy Python PASS**, test JS formularza/publikacji PASS,
node --check PASS. Wyniki odbioru serwerowego opisane na początku dokumentu.

```bash
python -B tools/run_isolated_tests.py tests.test_ghostlab_registry tests.test_ghostlab_publication tests.test_target_persistence.TargetPersistenceHelpersTest.test_ghostlab_published_tool_has_app_contract tests.test_target_persistence.TargetPersistenceHelpersTest.test_ghostlab_published_tool_preserves_requirements_and_googleplex_shape
node tests/js/test_ghostlab_publication.js
node --check static/js/terminal.js
```

Test HTTP blokuje odczyty/zapisy pełnych profili i SQL profile_json. Nowy
rejestr dodatkowo testuje wersje, przełączniki, blokadę planowanych szablonów,
klasyfikację narzędzi, izolację kopii i rozszerzenie nową definicją.
