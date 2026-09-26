# 145 — System Log Reader: runtime potomstwa

Status: implementacja lokalna; PASS wymaga odbioru serwerowego desktop/mobile.

### Odbiór użytkownika — 26 IX 2026

- PASS: aktualizacja Sysloga do v3, wersja zainstalowana i opublikowana zgodne.
- PASS: komunikaty runtime, odczyt potomkiem na celu PvP, wspólny limit rodziny,
  zmiana blueprintu i jawna aktualizacja.
- Mobile: zgłoszone boczne marginesy okna; poprawka pełnej szerokości przygotowana,
  ponowny odbiór wizualny pozostaje otwarty.

## Dostarczone

- Wspólny resolver inventory → produkt → niezmienny opublikowany artefakt.
  Jedyny nowy executor: system_log_reader/system_logs_v1. Pozostałe rodziny
  pozostają pending. Wbudowane narzędzia zachowują swoje wykonawce.
- Nowy compile zapisuje runtime_revision=1 dla System Log Readera. Stary build
  bez tego oznaczenia nie uruchamia się; potrzebuje compile/publish i instalacji
  albo jawnej aktualizacji. Nie migrujemy i nie nadpisujemy starych artefaktów.
- Odczyt do 5 rzeczywistych system_messages, istniejące statusy/limity tekstu;
  blueprint może zmniejszyć log_limit i ukryć type/status/created_at.
  Nie czytamy MailStore, prywatnych kanałów, payloadów wiadomości ani profili.
  Pusty wynik to sukces z pustą listą. Błąd store nie zużywa limitu.
- Rodzic i potomkowie korzystają ze wspólnego receipt systemLogReader dla dostępu.
  Retry jest odrzucane jako wykorzystany limit, zgodnie z rodzicem; nie odczytuje
  nowej treści. Receipt potomka zapisuje app/artifact/policy, bez tekstu logów.
- Odczyt, receipt i ponowne sprawdzenie dostępu, aresztu, instalacji i artefaktu
  w jednej transakcji. Publikacja nowego buildu nie podmienia instalacji.
  Request z nieaktualnym artifact_id wymaga odświeżenia panelu.
- Launcher pulpitu/FM/terminala używa tożsamości aplikacji, nie statycznych logów.
  Pokazuje aktualny cel PvP, wersję zainstalowaną i dostępną, stan odmowy/pending,
  przycisk odczytu i przycisk bezpłatnej jawnej aktualizacji.
- Aktualizacja: porównanie oczekiwanego i dostępnego artefaktu, wymagania i miejsce
  na dysku; atomowa wymiana aplikacji/launchera/zajętości i delty. Bez płatności,
  dodatkowego pobrania ani resetowania limitu rodziny. Retry nie duplikuje instalacji.
  Zmiana nazwy w buildzie aktualizuje pulpit/FM. Błąd delty cofa całą transakcję.

## Aktywacja

Nie wymaga migracji bazy ani ponownej migracji projektów/zabezpieczeń.
ecosystem.web.config.js zawiera:

```js
CHAOS_GHOSTLAB_LOG_RUNTIME_ENABLED: "true",
CHAOS_GHOSTLAB_RUNTIME_ACTORS: "main,admin",
```

Bez flagi runtime jest wyłączony. Pusta lista kont nikogo nie aktywuje.
Wildcard `*` oznacza wszystkich i nie jest ustawieniem początkowym.
Te flagi dotyczą wykonawcy potomka; publikacja i instalacja pozostają dostępne.
Po wgraniu kodu:

```sh
pm2 startOrRestart ecosystem.web.config.js --update-env
```

Ctrl+Shift+R na kontach testujących. Nie trzeba restartować workerów dla tego runtime.

## Odbiór krok po kroku

1. A = admin (autor), B = main (kupujący/wykonawca), C = trzeci gracz testowy.
   Zanotować salda A/B, miejsce B i dotychczasowy licznik pobrań produktu.
   C powinien mieć rozpoznawalny niedawny komunikat systemowy.
2. A: System Log Reader → własna nazwa/ikona/opis → log_limit=2,
   include_type/status/created_at=false → Save → Compile → Publish.
3. B: kupić z Googleplexa; sprawdzić kwotę do A i pojedyncze pobranie. Jeśli to
   już posiadany produkt, otworzyć go z pulpitu i użyć bezpłatnej aktualizacji.
4. Otworzyć launcher bez dostępu: czytelna odmowa, brak pozornego wyniku.
5. Uzyskać nowy dostęp do C. Potomek bez rodzica jest aktywny na liście PvP.
   Odczytać: do 2 ostatnich komunikatów C, bez ukrytych pól i prywatnej komunikacji.
   Wynik ma nazwę/ikonę/wersję kupionego potomka. Sprawdzić desktop i mobile.
6. Kolejna próba potomkiem, rodzicem lub drugim potomkiem tej rodziny: wykorzystany
   limit. Reconnect go nie resetuje. Wygasły dostęp, areszt i uninstall blokują odczyt.
7. A: kolejny build z log_limit=1, inną nazwą/ikoną. B przed aktualizacją nadal ma
   poprzedni artefakt. Aktualizuj: bez HC, bez dodatkowego pobrania; pulpit/FM/PvP
   pokazują nową markę. Ponowienie nie zmienia salda/licznika. Limit starego dostępu
   nadal wykorzystany; w nowym dostępie odczyt ma nowy limit.
8. Pusty zbiór system_messages: poprawny pusty wynik. Wycofanie sprzedaży nie
   odbiera wcześniej zainstalowanego, wspieranego buildu.

Dla starego Sysloga konieczne ponowne Compile/Publish: samo włączenie flagi
nie aktywuje historycznej instalacji. Używać UI aktualizacji, nie uninstall/rebuy.

## Diagnostyka i cofnięcie

Logi `GLAB_EXECUTION` zawierają actor, target, receipt, app, artifact, policy, status.
`GLAB_EXECUTION_DENIED` podaje status HTTP i powód, bez treści wiadomości.
Odczyt receipt:

```sql
SELECT id, attacker_username, victim_username, access_key, result, created_at
FROM player_hack_tool_usage WHERE tool_id='systemLogReader'
ORDER BY id DESC LIMIT 10;
```

Rollback: CHAOS_GHOSTLAB_LOG_RUNTIME_ENABLED="false" i restart weba z ecosystemu.
Nie usuwać publikacji, instalacji, transakcji ani receipts i nie cofać bazy.
Rodzic działa dalej; potomstwo pokazuje stan wyłączonego runtime.

## Walidacja lokalna

Testy wymuszają brak pełnych odczytów/zapisów profili, także SQL profile_json.
Regresja rodzica obejmuje konta 35 MB. Nowe testy: trzy konta, zakup/autor/pobrania,
parametry wyniku, podrobiony request, stary artefakt i flagi, retry/limit rodziny,
aktualizacja/płatność/zajętość/rollback, równoczesny odczyt, areszt i cofnięcie
dostępu w trakcie odczytu. JS: launcher, tożsamość produktu, aktualizacja i wynik.
Weryfikacja lokalna 25 IX: wszystkie 11 nowych przypadków runtime PASS;
10 regresji odczytu PvP (w tym duże profile) PASS; 16 publikacji i 7 rejestru PASS.
Po poprawce ponownej kompilacji legacy ponownie uruchomiono przypadek migracji
buildu oraz 23 testy publikacji/rejestru: PASS. Cztery skrypty JS (launcher i delty,
log reader, request guard, publikacja) PASS. Składnia JS i git diff --check PASS.
Celowo wstrzyknięte awarie store/delty zwracają błąd HTTP i wycofują transakcję;
ich traceback w testach jest oczekiwany. Nie jest to jeszcze PASS serwerowy.
