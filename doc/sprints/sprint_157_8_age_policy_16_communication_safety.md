# Sprint 157.8 — Polityka 16+ i bezpieczeństwo komunikacji

Data: 17 X 2026.
Status: **IMPLEMENTACJA LOKALNA — przed wdrożeniem i odbiorem produkcyjnym**. Aktywacja produkcyjna niezatwierdzona.

CHAOS ma pozostać otwartym, pseudonimowym światem z realnymi narzędziami ochrony użytkowników. Implementację bezpieczeństwa komunikacji oddzielamy od mechanizmu wieku. Ochrona kontaktu obejmuje wszystkich graczy, bez tworzenia klas wiekowych.

Dokument utrwala zakres 157.8.1–157.8.4. [Raport implementacji i ograniczenia](../audits/sprint_157_8_implementation.md) oraz [runbook](../runbooks/safety_157_8_rollout.md) opisują stan lokalny; nie nadano pełnego PASS. Powiązania: [Sprint 157](sprint_157_identity_gateway.md), [raport obecnego 18+](../audits/identity_18_report.md), [dotychczasowy runbook](../runbooks/identity_18_rollout.md).

## Zasady obowiązujące cały sprint

- Bez dokumentów tożsamości, daty urodzenia, PESEL i zewnętrznej identyfikacji wieku.
- Jedna polityka minimalnego wieku, jeden mechanizm backendowy; ponowne wykorzystanie Identity Gateway.
- Blokowanie dotyczy komunikacji. Nie zmienia PvP, klanów, konfliktów, własności ani informacji potrzebnych do rywalizacji.
- Zachowujemy konta, postępy, sesje i historię oświadczeń. Nie przepisujemy oświadczeń 18+ na 16+ i nie zdejmujemy automatycznie blokad wieku.
- `CHAOS_ADULT_POLICY_ENABLED=0` pozostaje na produkcji. Wdrożenie zabezpieczeń komunikacji nie aktywuje polityki wieku.
- Dokumenty prawne pozostają projektami do czasu zatwierdzenia. Nie deklarujemy zabezpieczeń, których nie wdrożono.

## 157.8.1 — Ochrona kontaktu dla wszystkich

Cel: gracz może skutecznie przerwać niechciany kontakt, również przy próbie obejścia interfejsu.

### Ponowne wykorzystanie

`MailStore` w `database.py`, kontakty i zaproszenia, kanały Cybernera, endpointy wiadomości w `run.py`, istniejące powiadomienia i synchronizacja zmian. Rozszerzamy obecne ścieżki zamiast tworzyć drugi komunikator.

### Zakres

1. Trwała lista blokad komunikacji oparta na stabilnych identyfikatorach kont.
2. Wspólny mechanizm sprawdzania uprawnień do kontaktu używany przy wysyłaniu wiadomości, zaproszeń i powiadomień.
3. Domyślnie DM od zaakceptowanych kontaktów. Osoba obca może wysłać ograniczone zaproszenie systemowe bez dowolnej treści, z limitami częstotliwości i ponawiania.
4. Blokada zatrzymuje prywatne wiadomości i zaproszenia między parą kont. Odpowiedź nadawcy nie ujawnia wprost faktu zablokowania.
5. W kanałach świata i klanu odbiorca może ukrywać zwykłe wypowiedzi zablokowanego autora. Systemowe informacje o walce, terytorium i klanie pozostają widoczne.
6. Historia pozostaje dostępna do zgłoszenia; blokowanie nie usuwa dowodów.
7. Odblokowanie nie przywraca automatycznie znajomości ani nie dostarcza odrzuconych wiadomości.
8. Przyciski blokowania i ustawienia kontaktu w stylu CHAOS, PL/EN, z komunikatami przy operacji.

### Migracja

Dodanie relacji blokad i ustawień kontaktu. Zachowanie istniejących zaakceptowanych znajomości. Dawna rozmowa bez zaakceptowanej znajomości nie staje się automatycznie zgodą na dalszy kontakt.

### Kryteria odbioru

- Blokada działa w API, po odświeżeniu, na drugim urządzeniu i w powiadomieniach.
- Bezpośrednie żądanie HTTP nie omija ustawień odbiorcy.
- Zaproszenia mają limity i nie służą do przesyłania dowolnego tekstu.
- Testy potwierdzają zachowanie PvP, klanów i konfliktów bez zmian.
- Regresja istniejących kontaktów, kanałów i synchronizacji.

## 157.8.2 — Zgłoszenia i minimalna obsługa moderacji

Cel: dostępna dla gracza ścieżka pomocy oraz narzędzia operatora do rozstrzygania zgłoszeń.

### Ponowne wykorzystanie

Układ panelu administracyjnego, wzorce formularzy i komunikatów, identyfikatory wiadomości oraz publikacji. Zgłoszenia bezpieczeństwa oddzielamy od developerskich raportów błędów i nie uzależniamy ich od trybu developerskiego.

### Zakres

1. Zgłoszenie wiadomości Cybernera, profilu lub publikacji BlackNetu.
2. Kategorie: nękanie, groźby, ujawnianie danych, niebezpieczne treści, spam.
3. Odniesienie do zgłoszonego obiektu i ograniczony kontekst potrzebny do oceny, bez kopiowania całej historii konta.
4. Tożsamość zgłaszającego niewidoczna dla zgłoszonego użytkownika.
5. Limity, obsługa duplikatów i potwierdzenie przy przycisku.
6. Kolejka administracyjna: nowe, rozpatrywane, rozstrzygnięte; uzasadnienie i historia działań.
7. Ukrycie konkretnej treści i czasowe ograniczenie komunikacji bez zmiany stanu rozgrywki.
8. Ścieżka odwołania. Zamknięcie zgłoszenia nie usuwa automatycznie dowodów; retencja wymaga decyzji.

### AI i BlackNet

- Zachować istniejące walidatory i bezpieczne szablony.
- Zinwentaryzować wejścia i wyjścia agentów; walidacja narracji nie oznacza ochrony wszystkich modułów AI.
- Umożliwić zgłoszenie i wycofanie szkodliwej publikacji oraz wyłączenie konkretnego źródła generowania bez zatrzymywania świata.
- Oznaczenia treści AI muszą odpowiadać rzeczywistemu pochodzeniu publikacji.

### Kryteria odbioru

- Pełna ścieżka zgłoszenie → decyzja → widoczny rezultat → odwołanie.
- Kontrola uprawnień moderatora, prywatności zgłaszającego i dostępu do dowodów.
- Zgłoszenie dostępne zwykłemu graczowi, PL/EN i mobile.
- Sankcja komunikacyjna nie narusza PvP i stanu świata.

## 157.8.3 — Jedna wersjonowana polityka wieku 16+

Cel: zmiana progu bez przebudowy logowania i bez reinterpretacji historii.

### Ponowne wykorzystanie

`identity_gateway/adult_policy.py`, tabela `identity_consents`, obecna bramka konta, wspólne formularze rejestracji oraz walidacja transakcyjna Identity Gateway.

### Zakres

1. Uogólnić obecny moduł do polityki minimalnego wieku, bez drugiej bramki.
2. Nowe oświadczenie PL: „Potwierdzam, że mam ukończone 16 lat.”
3. Nowe oświadczenie EN: „I confirm that I am at least 16 years old.”
4. Ścisła walidacja backendowa, nowa wersja oświadczenia i regulaminu.
5. Jednakowe wymagania przy rejestracji lokalnej oraz Google, Discord, GitHub i Steam.
6. Zachować wcześniejsze akceptacje. Nowa akceptacja jest oddzielnym rekordem; nie przepisujemy `18-v1` na `16-v1`.
7. Rozszerzyć zapis blokad o powód, próg i historię rozstrzygnięcia.
8. Istniejące `age_restricted` pozostają aktywne. Brakujące pochodzenie oznaczamy jako nieustalone, bez zgadywania wieku.
9. Indywidualny przegląd starej blokady. Zdjęcie blokady nie tworzy oświadczenia ani akceptacji regulaminu.
10. Zachować obsługę konta, wylogowanie i usunięcie przy odmowie lub blokadzie.

Nazewnictwo konfiguracji uporządkować z kompatybilnością: brak nowej konfiguracji ani stara flaga `0` nie mogą przypadkowo aktywować bramki. Nie ingerować w własność sesji i powiązania dostawców.

### Kryteria odbioru

- Wersjonowanie i atomowość zapisu; żadnej zgody utworzonej bez działania użytkownika.
- Nowe i stare konta, aktywne sesje, PWA, odmowa, ponowna akceptacja i blokady.
- „Poniżej 18” nie jest interpretowane jako „poniżej 16”.
- Zabezpieczenia komunikacji działają przy wyłączonej polityce wieku.
- Wszystkie zmiany pozostają nieaktywne produkcyjnie do osobnej decyzji.

## 157.8.4 — Dokumenty, odbiór i przygotowanie wdrożenia

Cel: gotowy pakiet do decyzji o uruchomieniu 16+, bez automatycznej aktywacji.

### Zakres

1. Projekty `/terms` i `/privacy` PL/EN zgodne z faktycznie wykonanymi zmianami.
2. Opis pseudonimowości, widoczności danych rozgrywki, kontaktu, blokowania, moderacji, AI i odwołań.
3. Macierz przepływów danych: zakres, cel, odbiorcy, uprawnienia i retencja.
4. Testy wszystkich dróg dostarczania komunikacji, powiadomień i już otwartych klientów.
5. Regresja PvP, klanów, konfliktów, publikacji i logowania.
6. UI przez Playwright na desktopie i mobile; oddzielny odbiór rzeczywistych OAuth i fizycznej PWA.
7. Migracje z dry-run, backupem, integralnością i idempotencją.
8. Oddzielna instrukcja wdrożenia ochrony komunikacji i późniejszej aktywacji wieku.
9. Macierz dowodów rozróżniająca testy lokalne, symulacje i odbiory produkcyjne.

### Wycofanie

Preferowany powrót do zgodnej wersji kodu, bez odtwarzania starej bazy świata. Nie kasować zgłoszeń, blokad ani oświadczeń. Awaria po uruchomieniu ochrony nie może po cichu otwierać zablokowanego kontaktu; dopuszczalne czasowe wyłączenie wysyłania wiadomości.

### Kryteria odbioru

- Udokumentowane wyniki regresji i brak niejawnych migracji zgód.
- Sprawdzona procedura wdrożenia i wycofania.
- Lista nierozstrzygniętych decyzji z właścicielem i statusem.
- Pełny PASS i aktywacja 16+ dopiero po dowodach oraz osobnym zatwierdzeniu operatora.

## Decyzje wymagane przed aktywacją 16+

| Obszar | Nierozstrzygnięta kwestia |
| --- | --- |
| Prawo i warunki usługi | Zakres obowiązków właściwych dla CHAOS, korzystanie przez osoby 16–17, odpłatność i ewentualne transakcje. Sam próg 16 nie rozstrzyga wszystkich kwestii. |
| Moderacja | Odpowiedzialni za zgłoszenia, pilne zagrożenia, sankcje i odwołania. |
| Prywatność | Lista publicznych pól, ustawienia obecności, uprawnienia administracyjne. |
| Retencja | Okresy przechowywania zgłoszeń, dowodów, blokad, logów, historii i backupów, także po usunięciu konta. |
| Usługi zewnętrzne i AI | Faktyczni dostawcy, przekazywane dane, miejsca przetwarzania i warunki wykorzystania. |
| Oświadczenie wieku | Ocena proporcjonalności deklaracji do rzeczywistych funkcji i ryzyka; checkbox nie stanowi pełnej oceny bezpieczeństwa. |
| Dane operatora | Potwierdzenie pełnego adresu; wcześniejszy zapis miejscowości i kodu wymaga wyjaśnienia. |

Wymagania prawne należy oddzielić od przyjętego minimum produktowego. Bezpieczeństwo kontaktu jest celem tego sprintu niezależnie od kwalifikacji prawnej usługi. Weryfikacja Google OAuth i opis przetwarzania danych pozostają osobnym zagadnieniem, nie uzasadnieniem progu 18+.

## Kolejność i granica wdrożenia

**157.8.1 → 157.8.2 → 157.8.3 → 157.8.4.**

Ochronę komunikacji można odebrać i wdrożyć wcześniej jako niezależną poprawę dla wszystkich. Aktywacja 16+ wymaga osobnej decyzji po rozstrzygnięciu kwestii prawnych, bezpieczeństwa i przetwarzania danych. Zapisanie tego planu nie zmienia produkcji.
