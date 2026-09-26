# Sprint 146 — GhostLab: pozostałe rodziny wykonawcze i domknięcie v1

Status: **PAKIET LOKALNY DO WDROŻENIA**, 26 IX 2026. Odbiór serwerowy otwarty.
Bez commita, pusha i wdrożenia. [Wspólny runbook i test trzech kont](../runbooks/sprint_146_ghostlab_runtime.md).

Poprzedni: [145 — pierwsza pełna ścieżka](sprint_145_ghostlab_system_log_reader.md).
Podstawa: [audyt](../audits/ghostlab_completion_audit_2026_09_24.md).

Uzupełnienie 26 IX: [porównanie zakładek Research, Ghost Exchange i Documentation](../audits/ghostlab_tabs_scope_2026_09_26.md).
146 domyka runtime obecnych rodzin, nie pełną ścieżkę rozwoju laboratorium.
Research, import/wymiana blueprintów i rozwój wersji są przypisane do GhostLab v2.0:
[149](sprint_149_ghostlab_v2_research.md) → [150](sprint_150_ghostlab_v2_exchange_import.md) →
[151](sprint_151_ghostlab_v2_community_versions.md) → [152](sprint_152_ghostlab_v2_completion.md),
dopiero po PASS kreatorów 147–148. Stan wyjściowy opisuje uzupełnienie audytu.

## Bramka: zero ciężkiego profilu

Wykryte naruszenie naprawiamy od razu w bieżącym etapie, z testem regresji;
nie odkładamy go do następnego sprintu ani jako długu technicznego.

Obowiązuje [wspólny zakaz ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Financial Sniffer używa walletu; Friend Kicker store relacji; Security Panel Proxy
wąskiego stanu i writera security; Arsenal Cleaner canonical inventory/storage.
Brak wydzielonego źródła oznacza konieczność jego przygotowania, nie odczyt profilu.
Każda rodzina musi przejść zero-heavy dla sukcesu, odmowy, retry i notyfikacji;
wykonawca odziedziczony po starym narzędziu nie jest zwolniony z tej bramki.

## Cel i rezultat

Sześć szablonów GhostLaba (pięć istniejących oraz Intruder Kicker dodany do planu
decyzją użytkownika z 25 IX) daje działające, zakupione i zainstalowane
narzędzia. Pięć rodzin modyfikujących stan używa wspólnych reguł Player Hack Access
i canonical zapisów gry. Publikacja aplikacji nie omija reguł aresztu, ochrony zasobów,
ryzyka, cooldownu ani jednokrotnego wykonania skutków.

## 146.1 — wspólny kontrakt skutków

- Rozszerzyć adapter z 145 o allowlistę kolejnych rodzin; zachować istniejące wykonawce
  i reguły domenowe zamiast kopiować ich logikę do GhostLaba.
- Rodziny rejestrować przez wspólny kontrakt przygotowany w 144.1–144.2 i wykonany
  w 145. Nie dodawać osobnych list szablonów ani ścieżek kreatora. Bilety,
  rozszerzenia dysku i nowe skanery wymagają osobnego zakresu aktywacji;
  146 uruchamia cztery pierwotnie planowane rodziny oraz Intruder Kicker.
- Zestawić każde pole blueprintu z rzeczywistym parametrem wykonawcy. Pole nie może
  obiecywać działania, które jest ignorowane: albo działa, albo jawnie pozostaje
  nieedytowalne/nieobsługiwane. Udokumentować precedence quality/reliability i limitów.
- Serwerowe limity w configu; porównać z balansem wbudowanych narzędzi. Zmiany balansu
  wykraczające poza istniejące reguły przedstawić autorowi przed aktywacją.
- Receipt obejmuje actor, target, app, artifact, policy, wynik losowania, koszty,
  efekty i status. Retry/wiele kart nie wykonują skutków ani losowania ponownie.
- Cooldown/limit użycia nie może być obchodzony przez przemianowanie, republish,
  nowy build, reinstall ani klon tego samego szablonu; oprzeć klucz na polityce
  rodziny i dostępu, nie wyłącznie na ID aplikacji.
- Sprawdzać dostęp, instalację i sankcje przy commit. Awaria nie pozostawia połowy
  transferu, usunięcia ani aktualizacji. Delta i komunikaty wynikają z zapisanego skutku.

## 146.2 — Financial Sniffer

- Parametry kradzieży, wykrycia i cooldownu ze zweryfikowanego artefaktu, ograniczone
  serwerową polityką; wspólna księga i atomowy transfer HC.
- Zdefiniować podstawę procentu, zaokrąglenie i granicę dostępnego salda przez reuse
  obecnej reguły; żadnych ujemnych sald ani tworzenia/utraty HC przy retry.
- Jawny odbiorca i powód każdego transferu. Opłaty systemowe, jeśli przewiduje je
  istniejąca polityka, trafiają do `admin`; nie wprowadzać nowych opłat w tym sprincie.
- PASS: kontrolowane saldo przed/po obu stronach, zgodny receipt i jedna zmiana
  mimo powtórzenia requestu; przypadki małego salda, cooldownu i utraty dostępu.

## 146.3 — Friend Kicker

- Dozwolona polityka wyboru kontaktu, prawdopodobieństwo i wykrycie; losowanie raz
  na wykonanie. Atakujący nie otrzymuje listy prywatnych kontaktów.
- Spójna zmiana relacji po obu stronach i właściwe komunikaty; pusta lista kontaktów
  daje jawny wynik bez fikcyjnego sukcesu.
- PASS: sukces, brak efektu, brak kandydatów i retry; bez naruszenia obcych relacji.

## 146.4 — Security Panel Proxy

- Odbiór serwerowy po aktywacji runtime potomka: konflikt wersji po zmianie przez
  ofiarę → Odśwież → aktualny stan → skuteczny kolejny zapis; ponowne otwarcie
  po zamknięciu okna/odświeżeniu strony bez nowego użycia i bez resetu czasu dostępu.
  Przeniesione z odbioru 144.3 decyzją użytkownika; marka, instalacja i stan
  runtime pending potomka mają już PASS, wykonanie tych operacji jeszcze nie.
- Tylko dozwolone przełączniki boolean i serwerowe presety; reuse `SECURITY_CONFLICTS`.
- Blueprint nie może definiować dowolnych nazw pól profilu, reguł bypass ani własnej
  macierzy uprawnień. Kontrola wersji stanu przy współbieżnej zmianie zabezpieczeń.
- PASS: dozwolona zmiana, konflikt reguł, zabronione pole, wygasły dostęp i równoległa
  zmiana przez właściciela; brak nadpisania niepowiązanych ustawień.

## 146.5 — Arsenal Cleaner

- Wybór kandydata i ochrona aplikacji według canonical inventory i serwerowej polityki;
  blueprint nie wyłącza ochrony core/system ani nie wskazuje cudzych ścieżek plików.
- Spójne usunięcie uprawnionego narzędzia z instalacji, FM, dysku i pulpitu przez
  istniejącą ścieżkę inventory; właściwa obsługa aktywnej operacji według obecnych reguł.
- PASS: jeden efekt mimo retry, brak kandydata, chroniona aplikacja, równoczesna
  konfiskata/uninstall; bez odtworzenia narzędzia po reconnectcie.

## 146.6 — regresja i odbiór GhostLab v1

### Intruder Kicker — dodatkowa rodzina

- Podłączyć kontrakt intruder_kicker z 144.3 do istniejącego execute_intruder_kicker.
- Sprawdzić instalację potomka i artefakt oraz aktualny dostęp PvP, relację intruza
  i własne terytorium. Branding ani parametry klienta nie rozszerzają kwalifikacji.
- Jedno użycie na dostęp wspólne dla wbudowanego narzędzia i potomstwa;
  republish, reinstall i klon nie odnawiają limitu. Zachować blokady aresztu.
- PASS: rzeczywiste wypchnięcie uprawnionego celu, odmowa poza własnym terytorium,
  wygasły dostęp, retry i zamiana wbudowanego narzędzia na potomka bez drugiego skutku.
- Cała ścieżka podlega zero-heavy; nie kopiować logiki transportu do GhostLaba.

### Wspólny odbiór

Każda rodzina korzysta z dynamicznego panelu PvP z 144.3: wyłącznie zainstalowane
produkty, poprawna nazwa/ikona potomka, bez placeholderów nieposiadanych rodziców.
Testować samo potomstwo oraz kilka produktów jednej rodziny bez obejścia limitów.

Macierz dla każdej rodziny: utworzenie → zapis → compile → preview → publish → zakup
przez drugiego gracza → instalacja → aktywny dostęp → użycie → rzeczywisty skutek.
Objąć co najmniej trzy konta i dwie sesje, desktop/mobile, restart/reconnect, retry,
wygaśnięcie dostępu, areszt, konfiskatę, aktualizację i wycofanie produktu.

- Potwierdzić balans i skutki na danych kontrolowanych; zachować dowody przed/po.
- Wbudowane narzędzia oraz instalator, Googleplex, księga HC i mechanizm konsekwencji
  muszą przejść odpowiednie regresje. Nie tworzyć podwójnych incydentów od jednego użycia.
- Aktywacja rodzin osobno przez konfigurację; zmienne procesu w ecosystemach.
  Runbook rollback wyłącza nowe wykonania, zachowuje historię i uzgadnia rozpoczęte
  operacje. Nie odwraca automatycznie prawidłowo wykonanych skutków.
- Zaktualizować dokumentację GhostLaba i statusy UI tak, by „działa” odpowiadało
  rzeczywiście odebranym szablonom. Pozostałe legacy artefakty pokazują powód blokady.
- Objąć tym także trzy zakładki: oznaczyć Research/Exchange jako fundament bez
  mechaniki, poprawić globalne Runtime Pending, kartę Runtime Roadmap i stałe
  preview w ghostlab_policy. Wymaganie Player Hack Access opisywać per kontrakt,
  nie dla wszystkich przyszłych szablonów. Odbiór 146 nie zamyka roadmapy v2.

Sprint jest PASS dopiero po odbiorze wszystkich pięciu rodzin i regresji System Log
Reader. Wtedy zamykamy **ścieżkę narzędzi GhostLab v1**, nie całą roadmapę v2.

## Poza zakresem trzech sprintów

Research Tree, Community/udostępnianie blueprintów, import `.glab`, AI Templates,
Plugin SDK, dowolny kod użytkownika i osobny Async Operation Runner. Nie są warunkiem
działania sześciu zaplanowanych szablonów PvP. Nowe assety/show nie są wymagane do odbioru runtime.

## Kolejne rozszerzenia — osobne sprinty, nie sekcje powyżej

Po bazowym 146: [146.1 — bilety](sprint_146_1_ghostlab_travel_tickets.md) →
[146.2 — czyszczenie i aktualizacja systemu](sprint_146_2_ghostlab_system_maintenance.md) →
[146.3 — firmware](sprint_146_3_ghostlab_firmware_maintenance.md) → 147.
Wspólny branding z 144.2 obejmuje edytowalną ikonę i opis każdego potomka.
