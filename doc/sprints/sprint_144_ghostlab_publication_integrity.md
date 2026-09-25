# Sprint 144 — GhostLab: projekty, buildy i poprawność publikacji

Status: **WDROŻONY / ROZSZERZENIA ZAPLANOWANE**, 24 IX 2026.
Potwierdzono UI main: projekt, trwała nazwa, Compile, Publish, katalog,
wycofanie i ponowna publikacja oraz czerwone potwierdzenie CHAOS.
Migracja main i 36 pozostałych kont zakończona bez błędów; dwa stare projekty
admina zachowane. Dostęp admin/robot potwierdzony przez użytkownika.
Nie oznacza to potwierdzenia wszystkich przypadków brzegowych odbioru.
Runbook, testy i ograniczenia:
[144 — implementacja i wdrożenie](../runbooks/sprint_144_ghostlab_publication.md).
Przed 145 dodano [144.1 — rejestr szablonów](sprint_144_1_ghostlab_template_registry.md)
i [144.2 — wspólny kreator](sprint_144_2_ghostlab_template_authoring.md).
Po audycie pro-toolsów dodano [144.3 — przypisania i admin](sprint_144_3_pro_tools_glab_alignment.md),
również jako warunek wejścia do 145.
To osobne rozszerzenia; historyczne numery sekcji poniżej pozostają bez zmian.
144.2 domyka też pozostałe testy odbioru bazowego 144.

Podstawa: [audyt GhostLaba](../audits/ghostlab_completion_audit_2026_09_24.md).
Następny: [145 — System Log Reader end to end](sprint_145_ghostlab_system_log_reader.md).

## Bramka: zero ciężkiego profilu

Wykryte naruszenie naprawiamy od razu w bieżącym etapie, z testem regresji;
nie odkładamy go do następnego sprintu ani jako długu technicznego.

Obowiązuje [wspólny zakaz ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
144 wydziela projekty/buildy z `profile.files`; CRUD, compile, export i Publisher
czytają store projektów oraz małą projekcję autora. Quality/price nie mogą pośrednio
wywoływać `get_profile()` ani `sync_session_profile()`. Legacy dane przenosi wyłącznie
osobna migracja operatorska. PASS wymaga testów i pomiaru zero-heavy całej ścieżki.

## Cel i rezultat

Autor publikuje dokładnie wskazany build własnego projektu. Dwóch autorów może
używać podobnych nazw projektów bez kolizji tożsamości i bez zastępowania cudzej
aplikacji. Edycja po kompilacji jednoznacznie wymaga nowego buildu przed publikacją
aktualnej wersji. Runtime narzędzi pozostaje nieaktywny do kolejnego sprintu.

## 144.1 — kontrakt projektu i migracja

- Trwałe globalnie unikalne `project_id`, właściciel, rewizja projektu i wersja schematu.
- Trwałe `app_id` niezależne od slugu, nazwy i numeru buildu; aktualizacje tego samego
  produktu nie tworzą przypadkowo kolejnego produktu.
- Build ma własne ID, rewizję wejścia, hash znormalizowanego blueprintu i wersję
  schematu/policy; opublikowanego artefaktu nie wolno edytować w miejscu.
- Zinwentaryzować legacy projekty, aplikacje i instalacje. Przygotować dry-run migracji
  oraz raport niejednoznacznych właścicieli/kolizji. Nie przypisywać autorstwa na podstawie
  samej nazwy ani automatycznie nadpisywać spornych rekordów.
- Zachować istniejące referencje zakupów i instalacji przez jawne mapowanie legacy ID.
  Wydzielić canonical store projektów z kontrolą rewizji; pełny odczyt i zapis profilu
  oraz zapis jego poddrzewa `files` są zakazane w runtime.

## 144.2 — schemat i compiler

- Zamknięta lista pięciu wspieranych szablonów, pól i polityk; custom notes mogą pozostać
  szkicem, ale nie dają wykonywalnego artefaktu.
- Odrzucać NaN, nieskończoności, bool zamiast liczby, wartości poza zakresem i nieznane
  reguły. Wymuszać integer dla liczników i parametrów wymagających wartości całkowitych.
- Zasady redakcji, ochrony aplikacji i konflikty security są serwerowe, nie dowolnym
  tekstem blueprintu. Teksty gracza nie definiują uprawnień ani kodu wykonawczego.
- Compile tworzy niezmienny snapshot konkretnej rewizji. Równoczesna edycja lub retry
  nie mogą po cichu zastąpić innego buildu; historia ma udokumentowane limity retencji,
  z zachowaniem artefaktów używanych przez publikacje i instalacje.

## 144.3 — Publisher i spójny zapis

- Sprawdzać autora istniejącej aplikacji po stronie backendu przy każdej aktualizacji.
- Publikacja wiąże konkretny build i rewizję; odmowa, jeśli bieżący projekt jest zmieniony
  względem buildu zgłoszonego jako aktualny. Stabilne powody błędów dla UI.
- Retry tej samej publikacji nie duplikuje produktu ani nie zmienia odbiorcy HC.
- Zapis katalogu i statusu projektu musi być atomowy albo mieć trwały, idempotentny
  mechanizm uzgodnienia po przerwaniu procesu. Równoległe publikacje nie gubią wpisów.
- Ustalić i opisać usuwanie szkicu, wycofanie produktu i aktualizacje instalacji.
  Wycofanie sprzedaży nie może niejawnie zmieniać właściciela lub usuwać zakupów.

## 144.4 — interfejs i zgodność legacy

- Czytelne stany: zmiany niezapisane, draft, skompilowany build, publikacja, runtime
  oczekujący. Nazwa „Ready” nie może sugerować działającej akcji przed Sprintem 145/146.
- Publisher pokazuje publikowaną wersję; niezapisane pola nie przechodzą pozornej
  walidacji jako część starszego buildu. Zachować Preview i eksport `.glab`.
- Import, Research i Community nie należą do tego sprintu.

## 144.5 — testy, migracja i odbiór

Warunki PASS:

1. Dwóch autorów z takim samym slugiem ma różne tożsamości produktów; próba aktualizacji
   cudzej aplikacji jest odrzucona i nie zmienia `purchase_account`.
2. Compile → zmiana blueprintu → Publish nie publikuje po cichu starego parametru.
3. Retry, równoległe publikacje i przerwanie między zapisami nie powodują duplikatu ani
   rozjazdu projektu z katalogiem.
4. Nieprawidłowy schemat jest odrzucany przed publikacją; poprawne pięć szablonów działa.
5. Migracja na kopii danych zachowuje zakupy, instalacje i autorstwo; sporne rekordy
   są raportowane. Rollback nie kasuje nowych danych.

Dostarczyć testy regresji, runbook migracji/dry-run/rollback i wyniki odbioru UI.
Samo przejście dotychczasowych dwóch testów metadanych nie zamyka sprintu.
