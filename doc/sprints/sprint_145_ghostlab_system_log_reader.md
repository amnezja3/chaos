# Sprint 145 — GhostLab: wspólny runtime i System Log Reader od projektu do działania

Status: **IMPLEMENTACJA — ODBIÓR SERWEROWY OTWARTY**, 25 IX 2026, po PASS 144.1–144.3.
Wdrożenie i odbiór: [runbook 145](../runbooks/sprint_145_ghostlab_runtime.md).

Poprzedni: [144 — poprawność publikacji](sprint_144_ghostlab_publication_integrity.md).
Przygotowanie: [144.1 — rejestr](sprint_144_1_ghostlab_template_registry.md),
[144.2 — wspólny kreator](sprint_144_2_ghostlab_template_authoring.md).
Bezpośrednia bramka: [144.3 — aktualizacja pro-toolsów i admin](sprint_144_3_pro_tools_glab_alignment.md).
Następny: [146 — pozostałe rodziny i domknięcie](sprint_146_ghostlab_runtime_completion.md).
Podstawa: [audyt](../audits/ghostlab_completion_audit_2026_09_24.md).

## Bramka: zero ciężkiego profilu

Wykryte naruszenie naprawiamy od razu w bieżącym etapie, z testem regresji;
nie odkładamy go do następnego sprintu ani jako długu technicznego.

Obowiązuje [wspólny zakaz ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Dotyczy także zakupu, instalatora, launchera, Player Hack Access i odczytu logów celu:
małe projekcje/store zamiast pełnego profilu autora, kupującego lub ofiary.
Stary helper wymagający pełnego profilu musi zostać dostosowany przed jego reuse.
PASS obejmuje test zero-heavy od zakupu do wyniku i odmowy, bez fallbacku sesji.

## Cel i rezultat

Gracz tworzy System Log Reader w GhostLabie, publikuje go, drugi gracz kupuje
i instaluje aplikację, a następnie używa jej na celu z aktywnym Player Hack Access.
Wynikiem są rzeczywiste, dozwolone komunikaty systemowe celu zgodne z blueprintem.
To pierwsza pełna ścieżka custom runtime; pozostałe pięć rodzin, w tym
Intruder Kicker dopisany do 144.3, oczekuje na 146.
Wykonanie korzysta z rejestru z 144.1: wspólny resolver, bramki, receipt i kontrakt
wyniku oraz osobny wykonawca SystemLogReader. Nie powstaje dedykowana ścieżka
publikacji/instalacji dla każdego szablonu. Target/access policy pochodzi z definicji;
Player Hack Access jest wymaganiem tej rodziny, nie wszystkich przyszłych narzędzi
(np. biletu lub rozszerzenia własnego dysku). Nowe rodziny z kontraktów 144.1
nie są automatycznie aktywowane w tym sprincie.

## 145.1 — resolver artefaktu i wspólna bramka wykonania

- Zainstalowane ID aplikacji prowadzi do canonical autora, produktu i niezmiennego
  artefaktu. Backend nie przyjmuje blueprintu ani uprawnień z requestu wykonania.
- Adapter dopuszcza wyłącznie `system_log_reader` o wspieranej wersji schematu.
  Brak artefaktu, niezgodność lub nieznany template kończą się czytelną odmową.
- Wykorzystać istniejący Player Hack Access oraz wykonawcę odczytu; nie tworzyć
  drugiego systemu dostępu ani interpretatora dowolnego kodu/komend.
- Wspólna kontrola: sesja, instalacja/własność narzędzia, aktualny cel i dostęp,
  ograniczenia aresztu. Ponowić konieczne kontrole przed udostępnieniem rezultatu.
- Powiązać request i receipt z konkretnym artefaktem; publikacja nowej wersji nie
  podmienia wersji w trakcie użycia. Wznowienie/retry zachowuje tę samą tożsamość.

## 145.2 — odczyt i polityka danych

- `log_limit` oraz dozwolone pola wyniku wynikają ze zweryfikowanego blueprintu,
  w granicach serwerowej polityki (obecnie maksymalnie 5 komunikatów).
- Wyłącznie dozwolone komunikaty systemowe; bez treści prywatnych wiadomości,
  rozmów klanowych, sekretów sesji i danych spoza aktywnego dostępu.
- Parametry redakcji nie mogą rozszerzać serwerowego zakresu danych.
- Pusty wynik jest poprawnym wynikiem odczytu, a nie błędem ani fikcyjnymi logami.
- Zasady ponownego odczytu, limitów i ewentualnego ryzyka porównać z obecnym
  System Log Reader; zachować wspólną politykę, bez arbitralnego nowego balansu.

## 145.3 — uruchamianie i prezentacja wyniku

- Podłączyć SystemLogReader do dynamicznej listy PvP z 144.3. Sam zainstalowany
  potomek wystarcza; przycisk używa jego tożsamości i artefaktu, bez wymagania
  instalacji rodzica. Wspólny limit rodziny obowiązuje także po zmianie produktu.

- Rzeczywisty launcher desktop/mobile dla zakupionej aplikacji GhostLab; nazwa,
  ikona i wersja odpowiadają produktowi, a nie wbudowanemu narzędziu.
- Wybór celu przez istniejącą ścieżkę Player Hack Access. Brak lub utrata dostępu
  daje zrozumiały komunikat; sam wybór celu nie daje uprawnień.
- Pokazać wynik, brak danych i odmowę jako odrębne stany. Nie emitować pozornego
  sukcesu na podstawie statycznych logów terminala.
- `runtime_status` oznacza działający runtime tylko dla obsługiwanego szablonu
  i artefaktu. Starszych publikacji nie aktywować masowo bez walidacji/migracji.

## 145.4 — testy całej ścieżki

Warunki PASS:

1. Autor A publikuje, gracz B kupuje i instaluje, gracz C jest celem; wynik odczytu
   odpowiada rzeczywistym komunikatom C i parametrom zainstalowanego buildu.
2. Zmiana limitu/pól w nowym buildzie daje przewidywalny efekt po jawnej aktualizacji.
3. Brak dostępu, wygasły dostęp, podrobione ID/blueprint, nieposiadane lub
   skonfiskowane narzędzie oraz areszt nie pozwalają na odczyt.
4. Retry/reconnect nie odnawiają uprawnień; wynik nie wycieka do innej sesji lub celu.
5. Prywatne treści nigdy nie są zwracane. Pusty wynik i błąd techniczny są rozróżnione.
6. Wbudowany System Log Reader nadal działa zgodnie z dotychczasową polityką.

## 145.5 — kontrolowana aktywacja

Przed PASS opisać i przetestować jawną aktualizację zainstalowanego produktu:
wersja zainstalowana vs dostępna, atomowa zamiana artefaktu, wymagania i miejsce
na dysku, ponowienie bez duplikacji/opłaty oraz niezmienny artefakt trwającej
operacji. Zmiana ceny katalogowej nie może sama pobierać HC. Jeśli aktualizacja
ma być płatna, wymaga osobnej jawnej zasady i potwierdzenia przed wdrożeniem;
nie wprowadzać arbitralnie opłat. Zakup potomka rozlicza canonical autora produktu,
nie admina tylko dlatego, że pro-tool źródłowy jest systemowy. Sprawdzić księgę,
retry i brak podwójnego wzrostu licznika pobrań.

Konfiguracja serwerowa ogranicza aktywację do tej rodziny i początkowo kont testowych;
zmienne wdrożeniowe zapisane w odpowiednich ecosystemach. Runbook zawiera przygotowanie
trzech kont, stan początkowy, instrukcję UI, dowody rezultatu i cofnięcie aktywacji.
Log diagnostyczny: execution/receipt, actor, target, app, artifact, policy, status i powód;
bez kopiowania odczytanej treści prywatnej lub sekretów do logów.

PASS wymaga testów backendu i ręcznego zakupu/instalacji/użycia na desktop/mobile.
Wyłączenie aktywacji nie usuwa produktów, instalacji ani receipts.
