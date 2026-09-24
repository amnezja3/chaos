# Sprint 145 — GhostLab: System Log Reader od projektu do działania

Status: **ZAPLANOWANY**, 24 IX 2026. Implementacja po PASS Sprintu 144.

Poprzedni: [144 — poprawność publikacji](sprint_144_ghostlab_publication_integrity.md).
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
To pierwsza pełna ścieżka custom runtime; pozostałe cztery rodziny nadal oczekują.

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

Konfiguracja serwerowa ogranicza aktywację do tej rodziny i początkowo kont testowych;
zmienne wdrożeniowe zapisane w odpowiednich ecosystemach. Runbook zawiera przygotowanie
trzech kont, stan początkowy, instrukcję UI, dowody rezultatu i cofnięcie aktywacji.
Log diagnostyczny: execution/receipt, actor, target, app, artifact, policy, status i powód;
bez kopiowania odczytanej treści prywatnej lub sekretów do logów.

PASS wymaga testów backendu i ręcznego zakupu/instalacji/użycia na desktop/mobile.
Wyłączenie aktywacji nie usuwa produktów, instalacji ani receipts.
