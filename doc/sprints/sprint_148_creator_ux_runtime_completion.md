# Sprint 148 — prosty UX, edycja projektów i bezpłatne aktualizacje

Status: **ZAPLANOWANY — nowe założenia 1 X 2026**, implementacja po PASS 147.
Kontrakt: [147](sprint_147_creator_gameplay_policy.md).
Zastępuje wcześniejszą wieloetapową ścieżkę; kreatory mają być prostsze od GhostLaba.

## 148.1 — jeden główny krok i końcowy edytor

**Nazwa + ikona + akcja/opcja mapy + czy tworzyć plik → generacja przez system
→ interfejs i publikacja.** Bez kolejnych formularzy rodzin, flag, plików i warunków.

Po generacji otwiera się odpowiednik ostatniego kroku obecnego kreatora. Preview,
opis oferty, cena i publikacja są na tym ekranie, nie w serii obowiązkowych kroków.
Pokazać realnie wylosowaną moc osobno od maksimum dostępnego dla poziomu.

| Kreator | Końcowy edytor |
| --- | --- |
| Term Creator | Lista wielu komend i odpowiadających outputów. Tekst nie jest wykonywalnym kodem. |
| Window Maker | Pierwszy ekran, logi i przyciski powiązane z systemowymi akcjami. |
| Button Choice / Button Maker | Prompt i zestaw opcji. `effect` widoczny dla wszystkich, działający dopiero od progu i po walidacji. |
| AppForge | Postęp i treści wyniku istniejącego typu aplikacji; ta sama prosta ścieżka i systemowo losowana moc. |

Warianty tekstów nie losują ponownie mocy. Preview nie wykonuje operacji ani
nie pobiera HC. Bezpieczne renderowanie; autorytatywny wynik pochodzi z backendu.

## 148.2 — ponowne otwarcie i edycja projektu

- Plik w katalogu twórcy otwiera istniejący projekt we właściwym kreatorze.
  Zachować ID projektu i produktu. Usuwanie/wycofanie jest osobną akcją.
  Brak kreatora daje komunikat, nie usuwa projektu ani nie instaluje automatycznie.
- Po publikacji można poprawiać literówki, nazwę/tytuł, opis, ikonę, logi,
  outputy i prezentację oferty. Przeznaczenie, tworzenie plików, mechaniki,
  moc, efekty, sposób działania oraz ceny są zablokowane także w API.
- Zmiana prezentacji komend/przycisków nie dodaje nowej akcji, płatności lub efektu.
  Edytor zachowuje ich powiązanie z zamrożoną mechaniką.
- Zapis szkicu zachowuje ten sam projekt; publikacja poprawki zastępuje ofertę
  pod tym samym ID. Nie powstaje drugi projekt ani duplikat w Googleplexie.
- Kontrola własności i rewizji, ochrona niezapisanych zmian. Dwie karty nie
  nadpisują sobie po cichu wersji. Nazwa jest prezentacją, a ID tożsamością.

## 148.3 — AKTUALIZACJA dla nabywcy

- Zakupiona kopia pozostaje niezmienna do świadomej aktualizacji przez użytkownika.
  Googleplex pokazuje wersję zainstalowaną/dostępną oraz **AKTUALIZACJA**.
- Nowe wydanie tej samej aplikacji jest dla wcześniejszego nabywcy bezpłatne.
  Bez kolejnego obciążenia HC, fikcyjnego przychodu twórcy i duplikatu instalacji.
- Retry aktualizacji jest idempotentne; docelowa wersja jest jednoznaczna również
  przy konkurencyjnej publikacji. Aktualizacja nie resetuje cooldownów i limitów.
- Wycofanie zachowuje kupione kopie. Aktualizacja nie może omijać pierwszego
  zakupu ani konfiskaty. Przed wdrożeniem dopiąć te stany do istniejącego kontraktu.

## 148.4 — wiedza i wykonanie gameplayowe

- Przygotować materiały szkoleniowe PTK w Googleplexie o zatwierdzonych efektach,
  wartościach i przykładach. Materiał uczy, nie przyznaje uprawnień.
- Button Choice wyjaśnia brak wpływu effect poniżej progu (roboczo LVL 100).
  Inne kreatory nie dają ręcznego pola. Losowe maksimum od LVL 40 to inna mechanika.
- Mapa wskazuje cel; aplikacja uruchamia przypisany executor. Brak celu,
  utrata dostępu, areszt, konfiskata i niezgodność wersji mają spójne komunikaty.
- Output, log i animacja nie udają skutku niezapisanego przez backend.
  Pełny pasek potężnego narzędzia sprawdzać na rzeczywistym stanie celu.

## 148.5 — rozliczenie opcji Button Choice

- Osobno pokazywać cenę zakupu i użycia. Przed kliknięciem znana kwota i odbiorca;
  zero oznacza bezpłatność. Backend pobiera cenę, autora i efekt z zainstalowanej wersji.
- Pierwsza publikacja zamraża ceny. Poprawki interfejsu nie przeliczają opłat.
- Jedno użycie to jeden receipt, transfer i efekt; retry/timeout/reconnect
  odtwarza wynik. Kolejne świadome użycie ma nową tożsamość.
- Odmowa walidacji, brak HC/celu/dostępu i błąd przed wykonaniem nie pobierają HC.
  Regułę opłaty za wykonaną, ale nieskuteczną próbę zatwierdzić przed aktywacją
  i jawnie pokazać w UI; nie uznawać starej propozycji za zatwierdzoną.
- Transfer i efekt są atomowe albo mają trwałą finalizację/odzyskiwanie.
  Obsłużyć równoległe wydatki, użycie własnej aplikacji bez sztucznego przychodu
  i brak odbiorcy. Proponowany fallback admin pozostaje do potwierdzenia,
  nigdy ciche zniszczenie HC. Naprawić stare fixture zamiast osłabiać walidację.

## Bramka i PASS

Obowiązuje [zero ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Osobny magazyn projektów, małe projekcje, kanoniczne inventory/wallet i receipts;
bez ciężkiego profilu autora, klienta czy celu także na błędach/retry.
Naruszenia naprawiać w bieżącym etapie.

Macierz czterech kreatorów: proste utworzenie → generacja → końcowy edytor →
publikacja → zakup na innym koncie → użycie → ponowne otwarcie projektu → korekta
prezentacji → ta sama oferta → stara kopia bez zmian → bezpłatna AKTUALIZACJA.
Sprawdzić brak duplikatów, oba salda i historię wersji.

Testy obejmują blokadę zmian mechaniki/ceny także przez API, zachowanie losowania,
różne moce na tym samym poziomie, próg effect, XMappera, zgodne cele/executory,
pliki i progres, free/min/max, retry, awarie, dwie karty, wycofanie, desktop/mobile
oraz klawiaturę. Wymagany odbiór gameplayowy, nie tylko wygląd formularza.

Kontrolowane wdrożenie z configiem i runbookiem. Rollback zachowuje projekty,
wersje, receipts i poprawne rozliczenia; nie przelicza kupionych narzędzi.

Po PASS: **149 — Research → 150 — Exchange/import → 151 — Community/wersje
→ 152 — domknięcie GhostLab v2.0**. Poza zakresem: dowolny kod gracza,
nowe zasady aresztu i incydentów oraz funkcje GhostLab v2.0.
